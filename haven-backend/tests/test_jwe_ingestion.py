import pytest
import json
import uuid
import datetime
from fastapi.testclient import TestClient
from jwcrypto import jwk, jwe

from app.main import app
from app.config import get_settings
from app.database.models import WeeklyEmployeeMetrics, BurnoutPrediction
from app.dependencies import get_behavioral_db

client = TestClient(app)

# Generate a consistent test key pair for tests
test_key = jwk.JWK.generate(kty='RSA', size=2048)
private_key_pem = test_key.export_to_pem(private_key=True, password=None).decode('utf-8')
public_key_pem = test_key.export_to_pem(private_key=False).decode('utf-8')

@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
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
    key_to_use = jwk.JWK.generate(kty='RSA', size=2048) if use_invalid_key else test_key
    jwetoken = jwe.JWE(payload.encode('utf-8'), recipient=key_to_use, protected=protected_header)
    return jwetoken.serialize(compact=True)

def test_full_prediction_flow(monkeypatch):
    # Mock the cache service
    mock_cache = {}
    invalidated_patterns = []
    
    class MockCacheService:
        def get(self, key): return mock_cache.get(key)
        def set(self, key, value, ttl): mock_cache[key] = value; return True
        def invalidate(self, pattern): invalidated_patterns.append(pattern); return 1
            
    from app.api import ingestion
    monkeypatch.setattr(ingestion, "get_cache_service", lambda: MockCacheService())
    
    # Mock model service
    class MockModelService:
        def is_available(self): return True
        def predict(self, metrics):
            return "High", {"Low": 0.1, "Medium": 0.2, "High": 0.7}, "Random Forest", "1.0"
            
    monkeypatch.setattr(ingestion.ModelService, "get_instance", lambda: MockModelService())
    
    # Mock SHAP service
    class MockShapService:
        def is_available(self): return True
        def explain(self, metrics):
            return {"explanations": {"High": {"top_positive": [{"feature": "avg_daily_work_hours", "contribution": 0.5}]}}}
            
    monkeypatch.setattr(ingestion, "get_shap_service", lambda: MockShapService())

    # We use a completely unique employee hash to avoid state pollution between runs
    emp_hash = f"test_full_flow_{uuid.uuid4().hex}"
    
    payload_dict = {
        "employee_hash": emp_hash,
        "week_start_date": "2026-10-05",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "request_id": str(uuid.uuid4()),
        "department": "Engineering",
        "avg_daily_work_hours": 10.5,
        "missing_checkout_count": None # missing field
    }
    jwe_str = create_jwe_payload(payload_dict)
    
    headers = {"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "created"
    assert data["prediction_status"] == "success"
    assert data["predicted_risk"] == "High"
    assert data["probabilities"]["High"] == 0.7
    
    # Verify cache invalidation
    assert f"prediction:*{emp_hash}*" in invalidated_patterns
    assert "dashboard:*" in invalidated_patterns
    
    # Test Idempotency (Duplicate update)
    payload_dict["request_id"] = str(uuid.uuid4()) # New request ID to pass replay protection
    payload_dict["department"] = "Sales"
    jwe_str_2 = create_jwe_payload(payload_dict)
    
    response2 = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str_2}, headers=headers)
    assert response2.status_code == 201
    assert response2.json()["action"] == "updated"

def test_expired_timestamp():
    payload_dict = {
        "employee_hash": "test_jwe_hash_expired",
        "week_start_date": "2026-10-05",
        "timestamp": (datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=10)).isoformat(),
        "request_id": str(uuid.uuid4())
    }
    jwe_str = create_jwe_payload(payload_dict)
    
    headers = {"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    assert response.status_code == 400
    assert "Request expired" in response.json()["detail"]

def test_invalid_encryption():
    payload_dict = {
        "employee_hash": "test_jwe_hash_invalid",
        "week_start_date": "2026-10-05"
    }
    jwe_str = create_jwe_payload(payload_dict, use_invalid_key=True)
    headers = {"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    assert response.status_code == 400

def test_invalid_service_token():
    payload_dict = {
        "employee_hash": "test_jwe_hash_token",
        "week_start_date": "2026-10-05"
    }
    jwe_str = create_jwe_payload(payload_dict)
    headers = {"X-Service-Token": "wrong-token"}
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    assert response.status_code == 401

def test_malformed_payload():
    payload_dict = {"department": "Engineering"}
    jwe_str = create_jwe_payload(payload_dict)
    headers = {"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    response = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    assert response.status_code == 400

def test_replay_protection(monkeypatch):
    mock_cache = {}
    class MockCacheService:
        def get(self, key): return mock_cache.get(key)
        def set(self, key, value, ttl): mock_cache[key] = value; return True
        def invalidate(self, pattern): return 1
            
    from app.api import ingestion
    monkeypatch.setattr(ingestion, "get_cache_service", lambda: MockCacheService())
    
    req_id = str(uuid.uuid4())
    payload_dict = {
        "employee_hash": "test_jwe_hash_replay",
        "week_start_date": "2026-10-05",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "request_id": req_id
    }
    jwe_str = create_jwe_payload(payload_dict)
    headers = {"X-Service-Token": "default_dev_service_token_replace_in_prod"}
    
    r1 = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    assert r1.status_code == 201
    
    r2 = client.post("/api/v1/ingestion/metrics", json={"jwe": jwe_str}, headers=headers)
    assert r2.status_code == 400
    assert "Replay attack detected" in r2.json()["detail"]
