from ai_interviewer_sdk import FoundryClient

from foundry_sdk_runtime.attachments import Attachment


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
