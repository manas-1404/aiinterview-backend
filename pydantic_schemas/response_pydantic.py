from pydantic import BaseModel
from typing import Optional, Dict, Any

class ResponseSchema(BaseModel):
    success: bool = True
    status_code: int
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None