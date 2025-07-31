from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TurnSchema(BaseModel):
    qaid: int
    question: Optional[str] = None
    answer: Optional[str] = None
    blocked: Optional[bool] = False
    clarity: Optional[int] = None
    composite_star: Optional[float] = None
    filler: Optional[float] = None
    iid: Optional[int] = None
    issues: Optional[str] = None
    justification: Optional[str] = None
    relevance: Optional[int] = None
    repair_attempts: Optional[int] = None
    safety_flags: Optional[str] = None
    star_a: Optional[int] = None
    star_r: Optional[int] = None
    star_s: Optional[int] = None
    star_t: Optional[int] = None
    target_competency: Optional[str] = None
    technical_depth: Optional[int] = None
    transcript_text: Optional[str] = None
    turn_index: Optional[int] = None
    uid: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
