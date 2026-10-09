from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.ingestion import HRMSMetricsPayload
from app.database.models import WeeklyEmployeeMetrics
from app.security.dependencies import verify_service_token
from app.dependencies import get_behavioral_db
import logging

router = APIRouter(
    prefix="/api/v1/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(verify_service_token)]
)

logger = logging.getLogger(__name__)

@router.post("/metrics", status_code=status.HTTP_201_CREATED)
def ingest_hrms_metrics(payload: HRMSMetricsPayload, db: Session = Depends(get_behavioral_db)):
    """
    Ingest weekly employee metrics from HRMS.
    Requires a valid service token in the X-Service-Token header.
    Idempotent: updates existing records for the same employee_hash and week_start_date.
    """
    try:
        existing = db.query(WeeklyEmployeeMetrics).filter(
            WeeklyEmployeeMetrics.employee_hash == payload.employee_hash,
            WeeklyEmployeeMetrics.week_start_date == payload.week_start_date
        ).first()

        if existing:
            # Update existing record
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            db.commit()
            return {"status": "success", "message": "Metrics updated successfully", "action": "updated"}
        else:
            # Create new record
            new_metric = WeeklyEmployeeMetrics(**payload.model_dump())
            # Fill mandatory fields if not present
            if not new_metric.schema_version:
                new_metric.schema_version = "1.0"
            if not new_metric.label_source:
                new_metric.label_source = "hrms_ingestion"
                
            db.add(new_metric)
            db.commit()
            return {"status": "success", "message": "Metrics created successfully", "action": "created"}

    except Exception as e:
        logger.error(f"Error ingesting metrics: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the metrics payload."
        )
