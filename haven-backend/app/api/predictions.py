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

from app.services.cache_service import CacheService, get_cache_service
from app.config import get_settings

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
    cache_service: CacheService = Depends(get_cache_service),
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
    
    import hashlib
    
    settings = get_settings()
    metadata = getattr(service, "_metadata", {})
    model_ver = metadata.get("version", metadata.get("model_version", "1.0"))
    
    # Generate input hash
    metrics_dict = request.metrics.model_dump()
    input_str = json.dumps(metrics_dict, sort_keys=True, default=str)
    input_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
    
    prediction_key = f"prediction:{request.metrics.employee_hash}:{request.metrics.week_start_date}:{model_ver}:{input_hash}"
    explanation_key = f"explanation:{prediction_key}"
    
    # Check cache for prediction
    cached_prediction = cache_service.get(prediction_key)
    
    explanation = None
    if request.include_explanations:
        cached_explanation = cache_service.get(explanation_key)
        if cached_explanation:
            explanation = cached_explanation
            
    # Return fully cached response if both are available (or if only prediction is requested and available)
    if cached_prediction and (not request.include_explanations or explanation):
        return PredictionResponse(
            predicted_risk=cached_prediction["predicted_risk"],
            probabilities=cached_prediction["probabilities"],
            model_type=cached_prediction["model_type"],
            model_version=cached_prediction["model_version"],
            explanation=explanation
        )
        
    try:
        # Recompute prediction if missing
        if not cached_prediction:
            predicted_risk, probabilities, model_type, model_version = service.predict(metrics_dict)
            cached_prediction = {
                "predicted_risk": predicted_risk,
                "probabilities": probabilities,
                "model_type": model_type,
                "model_version": model_version
            }
            # Invalidate old cache for this employee & week before saving new
            cache_service.invalidate(f"prediction:{request.metrics.employee_hash}:{request.metrics.week_start_date}:*")
            cache_service.invalidate(f"explanation:prediction:{request.metrics.employee_hash}:{request.metrics.week_start_date}:*")
            
            # Prediction data changes impact aggregate dashboards and graphs
            cache_service.invalidate("analytics:dashboard:*")
            cache_service.invalidate("analytics:graph:*")
            
            cache_service.set(prediction_key, cached_prediction, settings.cache_ttl_prediction)

        # Recompute explanation if missing
        if request.include_explanations and not explanation:
            if not shap_service.is_available():
                logger.warning("SHAP service is not available, skipping explanation.")
            else:
                explanation = shap_service.explain(metrics_dict)
                cache_service.set(explanation_key, explanation, settings.cache_ttl_prediction)
                
            # Store in Behavioral Vault when explanations are explicitly requested
            shap_explanations_json = json.dumps(explanation) if explanation else None
            prediction_create = BurnoutPredictionCreate(
                employee_hash=request.metrics.employee_hash,
                week_start_date=request.metrics.week_start_date,
                predicted_risk=cached_prediction["predicted_risk"],
                low_probability=cached_prediction["probabilities"].get("Low", 0.0),
                medium_probability=cached_prediction["probabilities"].get("Medium", 0.0),
                high_probability=cached_prediction["probabilities"].get("High", 0.0),
                shap_explanations=shap_explanations_json,
                model_type=cached_prediction["model_type"],
                model_version=cached_prediction["model_version"]
            )
            vault_service.save_prediction(prediction_create)
        
        response_data = PredictionResponse(
            predicted_risk=cached_prediction["predicted_risk"],
            probabilities=cached_prediction["probabilities"],
            model_type=cached_prediction["model_type"],
            model_version=cached_prediction["model_version"],
            explanation=explanation
        )
        
        return response_data
    except Exception as e:
        logger.error("Prediction failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction failed due to an internal error."
        )

@router.post("/predictions/explain", response_model=PredictionResponse)
def explain_burnout(
    request: PredictionRequest, 
    service: ModelService = Depends(get_model_service),
    shap_service: ShapService = Depends(get_shap_service),
    vault_service: BehavioralVaultService = Depends(get_behavioral_vault_service),
    cache_service: CacheService = Depends(get_cache_service),
    current_user: User = Depends(require_employee_or_above),
    behavioral_db: Session = Depends(get_behavioral_db)
):
    """
    Returns the prediction alongside the SHAP explanations and saves it to the behavioral vault.
    """
    request.include_explanations = True
    return predict_burnout(
        request=request,
        service=service,
        shap_service=shap_service,
        vault_service=vault_service,
        cache_service=cache_service,
        current_user=current_user,
        behavioral_db=behavioral_db
    )
