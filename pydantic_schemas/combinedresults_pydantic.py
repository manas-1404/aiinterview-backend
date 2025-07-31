from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CombinedResultSchema(BaseModel):
    rid: int
    total_score_25: float
    clarity_avg: float
    created_at: Optional[datetime] = None
    eval_confidence: Optional[float] = None
    filler_avg: float
    gaps: Optional[str] = None
    iid: int
    per_metric_weights: Optional[str] = None
    recommendation: str
    relevance_avg: float
    rubric_version: Optional[str] = None
    star_avg: float
    strengths: str
    technical_depth_avg: float
    turn_indices_used: Optional[str] = None
    uid: int
    updated_at: Optional[datetime] = None
    weaknesses: str
