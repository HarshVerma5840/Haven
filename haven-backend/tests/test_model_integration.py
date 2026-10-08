import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.services.model_service import ModelService
from app.api.predictions import get_model_service

client = TestClient(app)

def check_artifacts_exist():
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    return (
        os.path.exists(os.path.join(base, "random_forest_pipeline.joblib")) and
        os.path.exists(os.path.join(base, "random_forest_metadata.json")) and
        os.path.exists(os.path.join(base, "feature_columns.json"))
    )

@pytest.fixture(autouse=True)
def ensure_real_service():
    """Ensure the API uses the real singleton service instead of any overrides."""
    app.dependency_overrides.pop(get_model_service, None)
    yield

@pytest.mark.skipif(not check_artifacts_exist(), reason="Real model artifacts are missing. Skipping integration test.")
def test_real_model_prediction_api_success():
    service = ModelService.get_instance()
    assert service.is_available() is True
    
    payload = {
        "metrics": {
            "employee_hash": "hash123",
            "week_start_date": "2023-10-01",
            "department": "Engineering",
            "avg_daily_work_hours": 8.5,
            "tenure_months": 24.0,
            "github_commit_count": 15
        }
    }
    
    response = client.post("/api/v1/predictions", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "predicted_risk" in data
    assert data["predicted_risk"] in ["Low", "Medium", "High"]
    
    assert "probabilities" in data
    
    probs = data["probabilities"]
    assert "Low" in probs
    assert "Medium" in probs
    assert "High" in probs
    
    # Probabilities are between 0 and 1
    for p in probs.values():
        assert 0.0 <= p <= 1.0
        
    # Probabilities sum approximately to 1
    assert pytest.approx(sum(probs.values()), rel=1e-5) == 1.0
    
    assert "model_type" in data
    assert "model_version" in data
    assert "prediction_timestamp" in data
    
    # Ensure raw PII is not returned
    assert "employee_hash" not in data

@pytest.mark.skipif(not check_artifacts_exist(), reason="Real model artifacts are missing. Skipping integration test.")
def test_real_model_prediction_api_missing_values_and_unknown_categories():
    payload = {
        "metrics": {
            "employee_hash": "hash456",
            "week_start_date": "2023-10-08",
            "department": "Engineering_Secret_Dept", # Unknown category
            # Missing avg_daily_work_hours (numeric)
            # Extra fields
            "unknown_extra_field": "ignored"
        }
    }
    
    response = client.post("/api/v1/predictions", json=payload)
    assert response.status_code == 200 # Missing/unknown are handled gracefully
    data = response.json()
    assert "predicted_risk" in data

def test_prediction_api_invalid_input():
    payload = {
        "metrics": {
            "employee_hash": "hash789",
            "week_start_date": "2023-10-08",
            "avg_daily_work_hours": -5.0 # Invalid
        }
    }
    response = client.post("/api/v1/predictions", json=payload)
    assert response.status_code == 422

def test_real_model_prediction_api_model_unavailable():
    service = ModelService.get_instance()
    original_state = service._is_loaded
    service._is_loaded = False # Temporarily simulate unavailability
    
    try:
        payload = {
            "metrics": {
                "employee_hash": "hash123",
                "week_start_date": "2023-10-01"
            }
        }
        response = client.post("/api/v1/predictions", json=payload)
        assert response.status_code == 503
        assert response.json()["detail"] == "Model is currently unavailable."
    finally:
        service._is_loaded = original_state
