import os.path
from datetime import datetime

from ai_interviewer_sdk.ontology.objects import User
from fastapi import APIRouter, Depends, File, UploadFile, Request, HTTPException
from ai_interviewer_sdk import FoundryClient
from foundry_sdk_runtime.types import ReturnEditsMode, ActionConfig, ActionMode, SyncApplyActionResponse
from foundry_sdk.v1.ontologies.models import Attachment

from dependency.auth_dependency import authenticate_request
from pydantic_schemas.response_pydantic import ResponseSchema
from services.file_services import upload_file_to_foundry
from utils.utils import sanitize_filename_base

upload_router = APIRouter(
    prefix="/api/storage",
    tags=["Storage"]
)

@upload_router.post("/upload-file")
async def upload_file(request: Request, uploaded_file: UploadFile = File(...), jwt_payload: dict = Depends(authenticate_request)):
    """
    Endpoint to upload a file to foundry.
    """
    user_id = jwt_payload.get("sub")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if uploaded_file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF files are allowed."
        )

    file_bytes = uploaded_file.file.read()

    if len(file_bytes) > 5*1024*1024:
        return ResponseSchema(
            success=False,
            status_code=400,
            message="File size exceeds the maximum limit of 5MB.",
            data={}
        )

    temp_storage_dir = "temp"
    os.makedirs(temp_storage_dir, exist_ok=True)

    new_file_name = f"{user_id}_{sanitize_filename_base(name=user.name)}.pdf"

    temp_file_path = os.path.join(temp_storage_dir, new_file_name)

    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(file_bytes)

    try:

        file_attachment: Attachment | None = upload_file_to_foundry(palantir_client=palantir_client, file_path=temp_file_path)

        print(f"File URL: {file_attachment}")


        if file_attachment:

            new_cvid = palantir_client.ontology.queries.next_resume_cvidas_api()

            new_resume: SyncApplyActionResponse = palantir_client.ontology.actions.create_resume(
                action_config=ActionConfig(
                    mode=ActionMode.VALIDATE_AND_EXECUTE,
                    return_edits=ReturnEditsMode.ALL),
                cvid=new_cvid,
                uid=user_id,
                active=True,
                resume_file=file_attachment,
                created_at=datetime.today(),
                updated_at=datetime.today()
            )

            os.remove(temp_file_path)

            if new_resume.validation.result != "VALID":

                message = []
                for criteria in new_resume.validation.submission_criteria:
                    message.append(criteria)

                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to create resume: {message}"
                )

            return ResponseSchema(
                success=True,
                status_code=200,
                message="File uploaded successfully.",
                data={}
            )

        os.remove(temp_file_path)

        return ResponseSchema(
            success=False,
            status_code=500,
            message="File upload failed.",
            data={}
        )

    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return ResponseSchema(
            success=False,
            status_code=500,
            message=f"An error occurred while uploading the file",
            data={"Error": str(e)}
        )