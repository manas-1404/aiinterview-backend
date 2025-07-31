from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InterviewSessionSchema(BaseModel):
    iid: int
    uid: int
    jid: int
    status: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
