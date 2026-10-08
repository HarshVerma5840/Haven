from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.common import HealthResponse, ReadyResponse
from app.dependencies import get_db

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0"}

@router.get("/ready", response_model=ReadyResponse)
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed")
    
    return {"status": "ok", "database": db_status}
