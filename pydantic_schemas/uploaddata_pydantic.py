from pydantic import BaseModel

class UploadDataSchema(BaseModel):
    workExperience: str
    resumeSummary: str
    education: str
    projects: str
    skills: str
    cvid: int | None = None
