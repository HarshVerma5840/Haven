from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import date
from app.database.models import BurnoutPrediction

class BehavioralVaultRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_prediction_by_week_and_version(self, employee_hash: str, week_start_date: date, model_version: str) -> Optional[BurnoutPrediction]:
        return self.db.query(BurnoutPrediction).filter(
            BurnoutPrediction.employee_hash == employee_hash,
            BurnoutPrediction.week_start_date == week_start_date,
            BurnoutPrediction.model_version == model_version
        ).first()

    def save_prediction(self, prediction: BurnoutPrediction) -> BurnoutPrediction:
        try:
            self.db.add(prediction)
            self.db.commit()
            self.db.refresh(prediction)
            return prediction
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Prediction for this week and version already exists.")
            
    def update_prediction(self, record: BurnoutPrediction) -> BurnoutPrediction:
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_predictions_by_employee(self, employee_hash: str, skip: int = 0, limit: int = 100) -> List[BurnoutPrediction]:
        return self.db.query(BurnoutPrediction).filter(
            BurnoutPrediction.employee_hash == employee_hash
        ).order_by(BurnoutPrediction.week_start_date.desc()).offset(skip).limit(limit).all()
