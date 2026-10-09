from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.model_service import ModelService, ModelNotAvailableError
from app.security.dependencies import require_employee_or_above
from app.dependencies import get_db, get_behavioral_db
from app.database.models import User, RoleEnum
import structlog
import json

from app.services.shap_service import ShapService, get_shap_service
from app.services.behavioral_vault_service import BehavioralVaultService
from app.database.repositories.behavioral_vault_repository import BehavioralVaultRepository
from app.schemas.vault import BurnoutPredictionCreate

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["predictions"])

def get_model_service() -> ModelService:
    return ModelService.get_instance()
    
def get_behavioral_vault_service(db: Session = Depends(get_behavioral_db)) -> BehavioralVaultService:
    repo = BehavioralVaultRepository(db)
    return BehavioralVaultService(repo)

@router.post("/predictions", response_model=PredictionResponse)
def predict_burnout(
    request: PredictionRequest, 
    service: ModelService = Depends(get_model_service),
    shap_service: ShapService = Depends(get_shap_service),
    vault_service: BehavioralVaultService = Depends(get_behavioral_vault_service),
    current_user: User = Depends(require_employee_or_above),
    behavioral_db: Session = Depends(get_behavioral_db)
):
    if current_user.role == RoleEnum.EMPLOYEE:
        if current_user.employee_hash != request.metrics.employee_hash:
            raise HTTPException(status_code=403, detail="Employees can only access their own records.")
            
    elif current_user.role == RoleEnum.MANAGER:
        from app.database.models import WeeklyEmployeeMetrics
        target_employee_metrics = behavioral_db.query(WeeklyEmployeeMetrics).filter(WeeklyEmployeeMetrics.employee_hash == request.metrics.employee_hash).first()
        if not target_employee_metrics or target_employee_metrics.department != current_user.department:
            raise HTTPException(status_code=403, detail="Managers can only access records for their department.")
            
    if not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Model is currently unavailable."
        )
    
    try:
        metrics_dict = request.metrics.model_dump()
        predicted_risk, probabilities, model_type, model_version = service.predict(metrics_dict)
        
        explanation = None
        shap_explanations_json = None
        
        if request.include_explanations:
            if not shap_service.is_available():
                logger.warning("SHAP service is not available, skipping explanation.")
            else:
                explanation = shap_service.explain(metrics_dict)
                shap_explanations_json = json.dumps(explanation)
                
            # Store in Behavioral Vault when explanations are explicitly requested
            prediction_create = BurnoutPredictionCreate(
                employee_hash=request.metrics.employee_hash,
                week_start_date=request.metrics.week_start_date,
                predicted_risk=predicted_risk,
                low_probability=probabilities.get("Low", 0.0),
                medium_probability=probabilities.get("Medium", 0.0),
                high_probability=probabilities.get("High", 0.0),
                shap_explanations=shap_explanations_json,
                model_type=model_type,
                model_version=model_version
            )
            vault_service.save_prediction(prediction_create)
        
        return PredictionResponse(
            predicted_risk=predicted_risk,
            probabilities=probabilities,
            model_type=model_type,
            model_version=model_version,
            explanation=explanation
        )
    except Exception as e:
        logger.error("Prediction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed due to an internal error."
        )
