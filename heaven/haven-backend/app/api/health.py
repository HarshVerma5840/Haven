from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.common import HealthResponse, ReadyResponse
from app.dependencies import get_db
from app.services.model_service import ModelService
from app.security.dependencies import require_authenticated_user
from app.database.models import User
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0"}


@router.get("/ready", response_model=ReadyResponse)
@router.get("/api/v1/ready", response_model=ReadyResponse)
def readiness_check(db: Session = Depends(get_db), current_user: User = Depends(require_authenticated_user)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed")

    model_service = ModelService.get_instance()
    model_status = "ok" if model_service.is_available() else "unavailable"

    settings = get_settings()
    encryption_status = "ok" if settings.encryption_key else "unavailable"
    redis_status = "ok"

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
        "redis": redis_status,
        "encryption": encryption_status
    }
