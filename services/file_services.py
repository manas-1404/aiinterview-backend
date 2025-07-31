import httpx
import os

from ai_interviewer_sdk import FoundryClient

from utils.config import settings

from foundry_sdk_runtime.attachments import Attachment

def get_file_from_storage(object_url: str) -> str:
    """
    Download a file from a remote storage service.

    :param object_url: URL of the file to be downloaded.
    :return: Full path to the downloaded file if successful, False otherwise.
    """

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE}"
    }

    try:
        response = httpx.get(url=object_url, headers=headers)

        if response.status_code == 200:
            filename = object_url.split("/")[-1]

            os.makedirs("downloads", exist_ok=True)
            file_path = os.path.join("downloads", filename)

            with open(file_path, "wb") as file:
                file.write(response.content)

            return file_path
        else:
            print(f"Failed to download file: {response.status_code}")
            return "download_failed"

    except httpx.RequestError as e:
        print(f"An error occurred while downloading the file: {e}")
        return "download_failed"



def upload_file_to_foundry(palantir_client: FoundryClient, file_path: str) -> Attachment | None:
    attachment_name = "resume_file"
    try:
        attachment = palantir_client.ontology.attachments.upload(file_path, attachment_name)
        if hasattr(attachment, "rid") and attachment.rid:
            print("Upload successful! RID:", attachment.rid)
            return attachment
        else:
            print("Upload failed: No RID returned.")
            return None
    except Exception as e:
        print("Upload failed with exception:", e)
        return None
