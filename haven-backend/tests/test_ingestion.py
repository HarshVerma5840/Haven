import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ingest_metrics_unauthorized():
    payload = {
        "employee_hash": "test_hash",
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": 8.5
    }
    response = client.post("/api/v1/ingestion/metrics", json=payload)
    assert response.status_code == 422 # Because of missing header. If header provided but wrong, 401.

def test_ingest_metrics_invalid_token():
    payload = {
        "employee_hash": "test_hash",
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": 8.5
    }
    response = client.post(
        "/api/v1/ingestion/metrics",
        json=payload,
        headers={"X-Service-Token": "invalid_token"}
    )
    assert response.status_code == 401

def test_ingest_metrics_success():
    unique_hash = str(uuid.uuid4())
    payload = {
        "employee_hash": unique_hash,
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": 9.5,
        "overtime_hours": 2.5,
        "department": "Engineering"
    }
    
    # Create (Idempotent first call)
    response = client.post(
        "/api/v1/ingestion/metrics",
        json=payload,
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert response.status_code == 201
    assert response.json()["action"] == "created"

    # Update (Idempotent second call)
    payload["overtime_hours"] = 3.5
    response2 = client.post(
        "/api/v1/ingestion/metrics",
        json=payload,
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert response2.status_code == 201
    assert response2.json()["action"] == "updated"

def test_ingest_metrics_validation_error():
    payload = {
        "employee_hash": "test_hash_success",
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": -5.0 # Invalid negative hours
    }
    response = client.post(
        "/api/v1/ingestion/metrics",
        json=payload,
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert response.status_code == 422
