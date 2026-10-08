import pytest
from pydantic import ValidationError
from datetime import datetime, date
from app.schemas.prediction import PredictionRequest, RiskProbabilities, PredictionResponse

def test_valid_prediction_request():
    payload = {
        "metrics": {
            "employee_hash": "hash123",
            "week_start_date": "2023-10-01",
            "department": "Engineering",
            "avg_daily_work_hours": 8.5
        }
    }
    request = PredictionRequest(**payload)
    assert request.metrics.employee_hash == "hash123"
    assert request.metrics.week_start_date == date(2023, 10, 1)
    assert request.metrics.avg_daily_work_hours == 8.5

def test_invalid_fields_in_request():
    payload = {
        "metrics": {
            "employee_hash": "hash123",
            "week_start_date": "2023-10-01",
            "avg_daily_work_hours": -5.0  # Invalid, must be >= 0
        }
    }
    with pytest.raises(ValidationError) as exc:
        PredictionRequest(**payload)
    assert "Input should be greater than or equal to 0" in str(exc.value)

def test_valid_probabilities():
    probs = RiskProbabilities(Low=0.2, Medium=0.7, High=0.1)
    assert probs.Low == 0.2
    assert probs.Medium == 0.7
    assert probs.High == 0.1

def test_invalid_probabilities():
    with pytest.raises(ValidationError):
        # Probability > 1.0
        RiskProbabilities(Low=1.2, Medium=0.0, High=0.0)
        
    with pytest.raises(ValidationError):
        # Probability < 0.0
        RiskProbabilities(Low=-0.1, Medium=0.5, High=0.6)

def test_response_serialization():
    probs = RiskProbabilities(Low=0.2, Medium=0.7, High=0.1)
    response = PredictionResponse(
        predicted_risk="Medium",
        probabilities=probs,
        model_type="Random Forest",
        model_version="1.0"
    )
    
    # Check serialization
    data = response.model_dump()
    
    # Ensure raw PII is excluded
    assert "employee_hash" not in data
    assert "github_username" not in data
    assert "metrics" not in data
    
    # Ensure expected response shape
    assert data["predicted_risk"] == "Medium"
    assert data["probabilities"]["Low"] == 0.2
    assert data["schema_version"] == "1.0"
    assert isinstance(data["prediction_timestamp"], datetime)
