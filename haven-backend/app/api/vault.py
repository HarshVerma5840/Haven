from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db, get_identity_db, get_behavioral_db
from app.database.models import User, RoleEnum, WeeklyEmployeeMetrics
from app.security.dependencies import require_hr_admin, require_employee_or_above
from app.schemas.vault import (
    IdentityMappingCreate, 
    IdentityMappingResponse,
    BurnoutPredictionCreate,
    BurnoutPredictionResponse
)
from app.services.identity_vault_service import IdentityVaultService
from app.services.behavioral_vault_service import BehavioralVaultService
from app.services.identity_service import IdentityService
from app.database.repositories.identity_vault_repository import IdentityVaultRepository
from app.database.repositories.behavioral_vault_repository import BehavioralVaultRepository

router = APIRouter(prefix="/api/v1/vault", tags=["vault"])

def get_identity_vault_service(db: Session = Depends(get_identity_db)) -> IdentityVaultService:
    repo = IdentityVaultRepository(db)
    identity_service = IdentityService()
    return IdentityVaultService(repo, identity_service)

def get_behavioral_vault_service(db: Session = Depends(get_behavioral_db)) -> BehavioralVaultService:
    repo = BehavioralVaultRepository(db)
    return BehavioralVaultService(repo)

# --- Identity Vault Endpoints ---

@router.post("/identity", response_model=IdentityMappingResponse)
def create_identity_mapping(
    mapping: IdentityMappingCreate,
    service: IdentityVaultService = Depends(get_identity_vault_service),
    current_user: User = Depends(require_hr_admin) # strictly HR_ADMIN only
):
    """Create a raw identity mapping. Protected by HR_ADMIN RBAC."""
    try:
        return service.create_mapping(mapping)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/identity", response_model=List[IdentityMappingResponse])
def list_identity_mappings(
    skip: int = 0, limit: int = 100,
    service: IdentityVaultService = Depends(get_identity_vault_service),
    current_user: User = Depends(require_hr_admin)
):
    """List raw identity mappings. Protected by HR_ADMIN RBAC."""
    return service.list_mappings(skip=skip, limit=limit)

# --- Behavioral Vault Endpoints ---

@router.post("/behavioral/predictions", response_model=BurnoutPredictionResponse)
def save_prediction(
    prediction: BurnoutPredictionCreate,
    service: BehavioralVaultService = Depends(get_behavioral_vault_service),
    current_user: User = Depends(require_hr_admin) # Only internal systems/admins should save predictions
):
    """Persist a prediction to the behavioral vault."""
    try:
        return service.save_prediction(prediction)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/behavioral/predictions/{employee_hash}", response_model=List[BurnoutPredictionResponse])
def get_predictions(
    employee_hash: str,
    skip: int = 0, limit: int = 100,
    service: BehavioralVaultService = Depends(get_behavioral_vault_service),
    current_user: User = Depends(require_employee_or_above),
    db: Session = Depends(get_db)
):
    """Retrieve predictions for a specific employee_hash."""
    # RBAC rules for behavioral data
    if current_user.role == RoleEnum.EMPLOYEE and current_user.employee_hash != employee_hash:
        raise HTTPException(status_code=403, detail="Employees can only access their own records.")
    
    if current_user.role == RoleEnum.MANAGER:
        # Check if the employee belongs to the manager's department
        target_employee = db.query(User).filter(User.employee_hash == employee_hash).first()
        if not target_employee or target_employee.department != current_user.department:
            # Fallback to checking the metrics table directly if User table lacks the mapping
            # Metrics live in the behavioral vault!
            behavioral_db = service.repository.db
            metric = behavioral_db.query(WeeklyEmployeeMetrics).filter(
                WeeklyEmployeeMetrics.employee_hash == employee_hash
            ).first()
            if not metric or metric.department != current_user.department:
                raise HTTPException(status_code=403, detail="Managers can only access records for their department.")
    
    return service.get_predictions(employee_hash=employee_hash, skip=skip, limit=limit)
