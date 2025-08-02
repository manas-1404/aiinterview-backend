import os.path
from datetime import datetime

from ai_interviewer_sdk.ontology.objects import User
from fastapi import APIRouter, Depends, File, UploadFile, Request, HTTPException
from ai_interviewer_sdk import FoundryClient
from foundry_sdk_runtime.types import ReturnEditsMode, ActionConfig, ActionMode, SyncApplyActionResponse

from dependency.auth_dependency import authenticate_request
from pydantic_schemas.response_pydantic import ResponseSchema
from pydantic_schemas.uploaddata_pydantic import UploadDataSchema
from utils.utils import sanitize_filename_base

upload_router = APIRouter(
    prefix="/api/storage",
    tags=["Storage"]
)

@upload_router.post("/send-data")
async def upload_file(request: Request, data: UploadDataSchema, jwt_payload: dict = Depends(authenticate_request)):
    """
    Endpoint to upload a file to foundry.
    """
    user_id = jwt_payload.get("sub").get("uid")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    resume_raw = data.resumeSummary + "\n" + data.education + "\n" + data.workExperience + "\n" + data.projects + "\n" + data.skills

    try:

        new_cvid = palantir_client.ontology.queries.next_resume_cvidas_api()

        new_resume: SyncApplyActionResponse = palantir_client.ontology.actions.create_resume(
            action_config=ActionConfig(
                mode=ActionMode.VALIDATE_AND_EXECUTE,
                return_edits=ReturnEditsMode.ALL
            ),
            cvid=new_cvid,
            uid=user_id,
            active=True,
            education=data.education,
            workex=data.workExperience,
            projects=data.projects,
            resume_raw=resume_raw,
            skills=data.skills,
            parser_version="v1",
            resume_summary=data.resumeSummary,
            created_at=datetime.today(),
            updated_at=datetime.today()
        )

        if new_resume.validation.result != "VALID":
            message = [criteria for criteria in new_resume.validation.submission_criteria]
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create resume: {message}"
            )

        return ResponseSchema(
            success=True,
            status_code=200,
            message="Resume data uploaded successfully.",
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