from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class EmployeeDirectoryItem(BaseModel):
    """Anonymized behavioral summary for HR directory view."""
    employee_hash: str
    department: Optional[str] = None
    designation: Optional[str] = None
    current_burnout_risk: str = "Low"
    prediction_date: Optional[date] = None
    model_version: Optional[str] = "v1.2.0-prod"
    data_completeness: float = Field(default=100.0, ge=0.0, le=100.0)


class EmployeeDirectoryResponse(BaseModel):
    """Paginated response containing HR directory items."""
    items: List[EmployeeDirectoryItem]
    total: int
    page: int
    page_size: int
    pages: int
