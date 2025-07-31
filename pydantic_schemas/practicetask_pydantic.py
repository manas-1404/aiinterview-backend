from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PracticeTaskSchema(BaseModel):
    ptid: int
    competency: str
    actions: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    description: str
    due_date: datetime
    est_minutes: int
    ppid: int
    priority: Optional[str] = None
    status: Optional[str] = None
    success_criteria: Optional[str] = None
    uid: int
    updated_at: datetime
