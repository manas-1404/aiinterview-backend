from pydantic import BaseModel
from datetime import datetime

class UserSchema(BaseModel):
    uid: int
    role: str
    email: str
    name: str
    updated_at: datetime | None
    created_at: datetime | None