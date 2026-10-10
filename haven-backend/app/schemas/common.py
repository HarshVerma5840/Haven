from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    version: str | None = None
    
class ReadyResponse(BaseModel):
    status: str
    database: str
    model: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    model_error: str | None = None
    redis: str | None = "ok"
    encryption: str | None = "ok"
