from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.ingestion import HRMSMetricsPayload, EncryptedPayload
from app.database.models import WeeklyEmployeeMetrics, BurnoutPrediction
from app.security.dependencies import verify_service_token
from app.dependencies import get_behavioral_db
from app.security.encryption import decrypt_jwe
from app.services.cache_service import get_cache_service
from app.services.model_service import ModelService
from app.services.shap_service import get_shap_service
import logging
import json
import datetime

router = APIRouter(
    prefix="/api/v1/ingestion",
    tags=["Ingestion"],
    dependencies=[Depends(verify_service_token)]
)

logger = logging.getLogger(__name__)

@router.post("/metrics", status_code=status.HTTP_201_CREATED)
def ingest_hrms_metrics(enc_payload: EncryptedPayload, db: Session = Depends(get_behavioral_db)):
    """
    Ingest weekly employee metrics from HRMS securely via JWE.
    Requires a valid service token in the X-Service-Token header.
    Idempotent: updates existing records for the same employee_hash and week_start_date.
    Includes replay protection via CacheService.
    """
    cache = get_cache_service()
    try:
        decrypted_dict = decrypt_jwe(enc_payload.jwe)
        payload = HRMSMetricsPayload(**decrypted_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid encryption or payload: {e}")

    # Replay protection
    if payload.request_id:
        cache_key = f"replay:{payload.request_id}"
        if cache.get(cache_key):
            raise HTTPException(status_code=400, detail="Replay attack detected. Request ID already processed.")
        cache.set(cache_key, {"processed": True}, 300) # 5 min TTL

    if payload.timestamp:
        # Reject if older than 5 minutes
        dt_val = payload.timestamp
        if dt_val.tzinfo:
            dt_val = dt_val.replace(tzinfo=None)
        if datetime.datetime.utcnow() - dt_val > datetime.timedelta(minutes=5):
            raise HTTPException(status_code=400, detail="Request expired.")

    try:
        existing = db.query(WeeklyEmployeeMetrics).filter(
            WeeklyEmployeeMetrics.employee_hash == payload.employee_hash,
            WeeklyEmployeeMetrics.week_start_date == payload.week_start_date
        ).first()

        if existing:
            # Update existing record
            dumped = payload.model_dump(exclude_unset=True)
            dumped.pop('timestamp', None)
            dumped.pop('request_id', None)
            for key, value in dumped.items():
                setattr(existing, key, value)
            db.commit()
            action = "updated"
        else:
            # Create new record
            dumped = payload.model_dump()
            dumped.pop('timestamp', None)
            dumped.pop('request_id', None)
            new_metric = WeeklyEmployeeMetrics(**dumped)
            # Fill mandatory fields if not present
            if not new_metric.schema_version:
                new_metric.schema_version = "1.0"
            if not new_metric.label_source:
                new_metric.label_source = "hrms_ingestion"

            db.add(new_metric)
            db.commit()
            action = "created"

        prediction_status = "skipped"
        predicted_risk = None
        probabilities = None
        model_version = None

        try:
            model_service = ModelService.get_instance()
            shap_service = get_shap_service()

            if model_service.is_available():
                # Invalidate affected Redis cache entries
                cache.invalidate(f"prediction:*{payload.employee_hash}*")
                cache.invalidate("dashboard:*")

                metrics_dict = payload.model_dump()

                predicted_class, final_probs, model_type, m_version = model_service.predict(metrics_dict)
                predicted_risk = predicted_class
                probabilities = final_probs
                model_version = m_version

                shap_explanation = None
                if shap_service.is_available():
                    shap_explanation_dict = shap_service.explain(metrics_dict)
                    shap_explanation = json.dumps(shap_explanation_dict)

                prediction_record = db.query(BurnoutPrediction).filter(
                    BurnoutPrediction.employee_hash == payload.employee_hash,
                    BurnoutPrediction.week_start_date == payload.week_start_date,
                    BurnoutPrediction.model_version == m_version
                ).first()

                if not prediction_record:
                    prediction_record = BurnoutPrediction(
                        employee_hash=payload.employee_hash,
                        week_start_date=payload.week_start_date,
                        model_version=m_version
                    )
                    db.add(prediction_record)

                prediction_record.predicted_risk = predicted_class
                prediction_record.low_probability = final_probs.get("Low", 0.0)
                prediction_record.medium_probability = final_probs.get("Medium", 0.0)
                prediction_record.high_probability = final_probs.get("High", 0.0)
                prediction_record.model_type = model_type
                prediction_record.shap_explanations = shap_explanation

                db.commit()
                prediction_status = "success"
            else:
                prediction_status = "model_unavailable"
        except Exception as e:
            logger.warning(f"Failed to generate prediction synchronously: {e}")
            db.rollback()
            prediction_status = "failed"

        return {
            "status": "success",
            "message": f"Metrics {action} successfully",
            "action": action,
            "prediction_status": prediction_status,
            "predicted_risk": predicted_risk,
            "probabilities": probabilities,
            "model_version": model_version,
            "prediction_timestamp": datetime.datetime.utcnow().isoformat(),
            "request_id": payload.request_id
        }

    except Exception as e:
        logger.error(f"Error ingesting metrics: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the metrics payload."
        )
