from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
from app.schemas.metrics import WeeklyEmployeeMetricsInput

class PredictionRequest(BaseModel):
    """
    Request payload wrapping the weekly metrics.
    Note: WeeklyEmployeeMetricsInput already makes burnout_score and burnout_risk optional,
    and we ignore them during prediction.
    """
    metrics: WeeklyEmployeeMetricsInput

class RiskProbabilities(BaseModel):
    """
    Strictly typing the probability values.
    """
    Low: float = Field(..., ge=0.0, le=1.0, description="Probability of Low risk")
    Medium: float = Field(..., ge=0.0, le=1.0, description="Probability of Medium risk")
    High: float = Field(..., ge=0.0, le=1.0, description="Probability of High risk")

class PredictionResponse(BaseModel):
    """
    The output of the prediction service.
    Excludes any raw employee IDs or GitHub usernames to maintain privacy.
    """
    predicted_risk: Literal["Low", "Medium", "High"] = Field(..., description="Predicted burnout risk")
    probabilities: RiskProbabilities = Field(..., description="Class probabilities between 0 and 1")
    model_type: str = Field(..., description="Type of the model used (e.g., Random Forest)")
    model_version: str = Field(..., description="Version of the model artifacts")
    schema_version: str = Field(default="1.0", description="API Schema version")
    prediction_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
