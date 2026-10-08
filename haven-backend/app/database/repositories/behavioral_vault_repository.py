from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import date
from app.database.models import WeeklyEmployeeMetrics

class BehavioralVaultRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee_and_week(self, employee_hash: str, week_start_date: date) -> Optional[WeeklyEmployeeMetrics]:
        return self.db.query(WeeklyEmployeeMetrics).filter(
            WeeklyEmployeeMetrics.employee_hash == employee_hash,
            WeeklyEmployeeMetrics.week_start_date == week_start_date
        ).first()

    def update(self, record: WeeklyEmployeeMetrics) -> WeeklyEmployeeMetrics:
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_predictions_by_employee(self, employee_hash: str, skip: int = 0, limit: int = 100) -> List[WeeklyEmployeeMetrics]:
        return self.db.query(WeeklyEmployeeMetrics).filter(
            WeeklyEmployeeMetrics.employee_hash == employee_hash,
            WeeklyEmployeeMetrics.model_version.isnot(None)
        ).order_by(WeeklyEmployeeMetrics.week_start_date.desc()).offset(skip).limit(limit).all()
