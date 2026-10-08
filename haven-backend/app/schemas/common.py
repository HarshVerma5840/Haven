from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    version: str | None = None
    
class ReadyResponse(BaseModel):
    status: str
    database: str
    model: str | None = None
