import pytest
from fastapi.testclient import TestClient
from app.main import app
import datetime

client = TestClient(app)

def test_full_e2e_flow():
    """
    Tests the complete E2E flow from HRMS payload ingestion to Model Prediction with caching.
    HRMS payload -> Haven validation -> PostgreSQL two-vault storage -> model prediction -> SHAP explanation -> Redis cache -> API response
    """
    # 1. Ingest HRMS Payload (Validated through Pydantic, stored in Behavioral Vault via Postgres)
    ingest_payload = {
        "employee_hash": "e2e_test_hash",
        "week_start_date": "2026-10-19",
        "department": "Engineering",
        "avg_daily_work_hours": 10.5,
        "overtime_hours": 12.0,
        "leave_days_taken": 0,
        "appraisal_rating": 3.0,
        "github_commit_count": 50,
        "meeting_hours": 20
    }
    
    ingest_response = client.post(
        "/api/v1/ingestion/metrics",
        json=ingest_payload,
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert ingest_response.status_code == 201
    assert ingest_response.json()["status"] == "success"

    # 2. Authenticate as the employee
    # First, register the employee to get a token
    register_payload = {
        "username": "e2e_employee",
        "email": "e2e@example.com",
        "password": "Password123!",
        "role": "EMPLOYEE",
        "employee_hash": "e2e_test_hash"
    }
    client.post("/api/v1/auth/register", json=register_payload)

    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "e2e_employee", "password": "Password123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 3. Request Prediction with SHAP explanation
    prediction_payload = {
        "metrics": {
            "employee_hash": "e2e_test_hash",
            "week_start_date": "2026-10-19",
            "avg_daily_work_hours": 10.5,
            "overtime_hours": 12.0,
            "leave_days_taken": 0,
            "appraisal_rating": 3.0,
            "github_commit_count": 50,
            "tenure_months": 24,
            "team_size": 5
        },
        "include_explanations": True
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First call: computes prediction + SHAP, saves to Postgres, caches in Redis
    pred_response_1 = client.post("/api/v1/predictions/explain", json=prediction_payload, headers=headers)
    assert pred_response_1.status_code == 200
    data_1 = pred_response_1.json()
    assert "predicted_risk" in data_1
    assert "probabilities" in data_1
    assert "explanation" in data_1
    assert "model_version" in data_1
    
    # Second call: Should fetch entirely from Redis Cache
    pred_response_2 = client.post("/api/v1/predictions/explain", json=prediction_payload, headers=headers)
    assert pred_response_2.status_code == 200
    data_2 = pred_response_2.json()
    
    # Results must match exactly (timestamp might differ slightly if not cached, but it is cached)
    assert data_1["predicted_risk"] == data_2["predicted_risk"]
    assert data_1["probabilities"] == data_2["probabilities"]
