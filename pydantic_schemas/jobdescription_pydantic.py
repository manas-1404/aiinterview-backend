from pydantic import BaseModel

class JobDescriptionSchema(BaseModel):
    jid: int | None = None
    role: str
    company: str
    jd_summary: str
    min_qualifications: str
    preferred_qualifications: str