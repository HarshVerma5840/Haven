import pytest
import uuid
import json
import datetime
from fastapi.testclient import TestClient
from app.main import app
from jwcrypto import jwk, jwe
from unittest.mock import MagicMock

client = TestClient(app)

# Generate a consistent test key pair for tests
test_key = jwk.JWK.generate(kty='RSA', size=2048)
private_key_pem = test_key.export_to_pem(private_key=True, password=None).decode('utf-8')

@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "haven_encryption_private_key", private_key_pem)
    yield

def create_jwe_payload(payload_dict: dict, use_invalid_key=False):
    payload = json.dumps(payload_dict)
    protected_header = {
        "alg": "RSA-OAEP-256",
        "enc": "A256GCM",
        "kid": "test-kid"
    }
    k = jwk.JWK.generate(kty='RSA', size=2048) if use_invalid_key else test_key
    jwetoken = jwe.JWE(payload.encode('utf-8'), recipient=k, protected=protected_header)
    return jwetoken.serialize(compact=True)

def test_ingest_metrics_unauthorized():
    payload = {
        "employee_hash": "test_hash",
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": 8.5,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "request_id": str(uuid.uuid4())
    }
    jwe_str = create_jwe_payload(payload)
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str})
    assert response.status_code == 422 # Because of missing header.

def test_ingest_metrics_invalid_token():
    payload = {
        "employee_hash": "test_hash",
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": 8.5,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "request_id": str(uuid.uuid4())
    }
    jwe_str = create_jwe_payload(payload)
    response = client.post(
        "/api/v1/ingestion/metrics",
        json={"jwe": jwe_str},
        headers={"X-Service-Token": "invalid_token"}
    )
    assert response.status_code == 401

def test_ingest_metrics_success_and_duplicate():
    unique_hash = str(uuid.uuid4())
    req_id1 = str(uuid.uuid4())
    payload = {
        "employee_hash": unique_hash,
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": 9.5,
        "overtime_hours": 2.5,
        "department": "Engineering",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "request_id": req_id1
    }

    jwe_str1 = create_jwe_payload(payload)

    # Create (Idempotent first call)
    response = client.post(
        "/api/v1/ingestion/metrics",
        json={"jwe": jwe_str1},
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert response.status_code == 201
    assert response.json()["action"] == "created"

    # Update (Idempotent second call, must use new request_id to avoid replay protection)
    req_id2 = str(uuid.uuid4())
    payload["overtime_hours"] = 3.5
    payload["request_id"] = req_id2
    jwe_str2 = create_jwe_payload(payload)

    response2 = client.post(
        "/api/v1/ingestion/metrics",
        json={"jwe": jwe_str2},
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert response2.status_code == 201
    assert response2.json()["action"] == "updated"

def test_ingest_metrics_validation_error():
    payload = {
        "employee_hash": "test_hash_success",
        "week_start_date": "2026-10-12",
        "avg_daily_work_hours": -5.0, # Invalid negative hours
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "request_id": str(uuid.uuid4())
    }
    jwe_str = create_jwe_payload(payload)
    response = client.post(
        "/api/v1/ingestion/metrics",
        json={"jwe": jwe_str},
        headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    )
    assert response.status_code == 400

from unittest.mock import patch

def test_replay_protection():
    req_id = str(uuid.uuid4())
    payload = {
        "employee_hash": "replay_test",
        "week_start_date": "2026-10-12",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "request_id": req_id
    }
    jwe_str = create_jwe_payload(payload)

    with patch("app.api.ingestion.get_cache_service") as mock_get_cache:
        mock_cache = MagicMock()
        mock_cache.get.side_effect = [None, {"processed": True}]
        mock_get_cache.return_value = mock_cache

        r1 = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"})
        assert r1.status_code == 201

        r2 = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"})
        assert r2.status_code == 400
        assert "Replay attack" in r2.json()["detail"]

def test_invalid_jwe():
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": "invalid.jwe.token"}, headers={"X-Service-Token": "default_dev_service_token_replace_in_prod"})
    assert response.status_code == 400
