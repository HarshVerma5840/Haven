from typing import Optional, List
from datetime import date

from app.database.models import WeeklyEmployeeMetrics
from app.schemas.vault import BurnoutPredictionCreate
from app.database.repositories.behavioral_vault_repository import BehavioralVaultRepository

class BehavioralVaultService:
    def __init__(self, repository: BehavioralVaultRepository):
        self.repository = repository

    def save_prediction(self, prediction_in: BurnoutPredictionCreate) -> WeeklyEmployeeMetrics:
        """
        Saves a prediction to the behavioral vault. Only uses employee_hash.
        """
        existing = self.repository.get_by_employee_and_week(
            employee_hash=prediction_in.employee_hash,
            week_start_date=prediction_in.week_start_date
        )
        
        if existing:
            for key, value in prediction_in.model_dump().items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            return self.repository.update(existing)
        else:
            raise ValueError("Weekly metrics record does not exist for this employee/week. Cannot save prediction.")

    def get_predictions(self, employee_hash: str, skip: int = 0, limit: int = 100) -> List[WeeklyEmployeeMetrics]:
        return self.repository.get_predictions_by_employee(employee_hash, skip, limit)
