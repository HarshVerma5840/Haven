from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

# Identity Vault Schemas
class IdentityMappingCreate(BaseModel):
    email: Optional[str] = None
    github_username: Optional[str] = None
    hrms_employee_id: Optional[str] = None
    # Provide at least one identifier to hash

class IdentityMappingResponse(BaseModel):
    id: int
    employee_hash: str
    email: Optional[str] = None
    github_username: Optional[str] = None
    hrms_employee_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Analytical Vault Schemas
class BurnoutPredictionCreate(BaseModel):
    employee_hash: str
    week_start_date: date
    burnout_risk: str
    probability_low: float
    probability_medium: float
    probability_high: float
    shap_explanations: Optional[str] = None
    model_version: str

class BurnoutPredictionResponse(BurnoutPredictionCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
