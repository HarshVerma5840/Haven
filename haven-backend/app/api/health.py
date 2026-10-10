from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.common import HealthResponse, ReadyResponse
from app.dependencies import get_db
from app.services.model_service import ModelService
from app.security.dependencies import require_authenticated_user
from app.database.models import User

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0"}

@router.get("/ready", response_model=ReadyResponse)
def readiness_check(db: Session = Depends(get_db), current_user: User = Depends(require_authenticated_user)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed")
    model_service = ModelService.get_instance()
    is_model_ok = model_service.is_available()
    model_status = "ok" if is_model_ok else "unavailable"
    model_name = model_service.get_model_name()
    model_version = model_service.get_model_version() if is_model_ok else None
    model_error = model_service.get_load_error()
    
    if db_status == "error" or model_status == "unavailable":
        status_overall = "error"
        if db_status == "error":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed")
    else:
        status_overall = "ok"
    
    return {
        "status": status_overall,
        "database": db_status,
        "model": model_status,
        "model_name": model_name,
        "model_version": model_version,
        "model_error": model_error
    }
