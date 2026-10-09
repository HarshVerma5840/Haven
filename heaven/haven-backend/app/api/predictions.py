from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.prediction import PredictionRequest, PredictionResponse
from app.services.model_service import ModelService, ModelNotAvailableError
from app.security.dependencies import require_employee_or_above
from app.database.models import User, RoleEnum
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["predictions"])

def get_model_service() -> ModelService:
    return ModelService.get_instance()

@router.post("/predictions", response_model=PredictionResponse)
def predict_burnout(
    request: PredictionRequest, 
    service: ModelService = Depends(get_model_service),
    current_user: User = Depends(require_employee_or_above)
):
    if current_user.role == RoleEnum.EMPLOYEE:
        if current_user.employee_hash != request.metrics.employee_hash:
            raise HTTPException(status_code=403, detail="Employees can only access their own records.")
            
    elif current_user.role == RoleEnum.MANAGER:
        if not current_user.department or current_user.department != request.metrics.department:
            raise HTTPException(status_code=403, detail="Managers can only access records for their department.")
            
    if not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="Model is currently unavailable."
        )
    
    try:
        predicted_risk, probabilities, model_type, model_version = service.predict(request.metrics)
        
        return PredictionResponse(
            predicted_risk=predicted_risk,
            probabilities=probabilities,
            model_type=model_type,
            model_version=model_version
        )
    except Exception as e:
        logger.error("Prediction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed due to an internal error."
        )
