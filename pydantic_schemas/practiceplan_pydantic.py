from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PracticePlanSchema(BaseModel):
    ppid: int
    overall_goal: str
    approved_at: Optional[datetime] = None
    approved_by: Optional[float] = None
    created_at: datetime
    created_by: Optional[str] = None
    decline_reason: Optional[str] = None
    iid: int
    motivation_note: str
    next_session_suggested_days: Optional[int] = None
    plan_version: Optional[str] = None
    reading_list: Optional[str] = None
    status: str
    uid: int
    updated_at: datetime
