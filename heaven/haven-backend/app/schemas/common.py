from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    version: Optional[str] = None


class ReadyResponse(BaseModel):
    status: str
    database: str
    model: Optional[str] = None
    redis: Optional[str] = "ok"
    encryption: Optional[str] = "ok"
