from pydantic import BaseModel
from datetime import datetime

class UserResponse(BaseModel):
    uid: int
    role: str
    email: str
    name: str
    updated_at: datetime | None
    created_at: datetime | None