import time
import uuid
import pytest
from jose import jwt
from app.config import get_settings

settings = get_settings()
SECRET = settings.sso_secret if settings.sso_secret else settings.jwt_secret

def make_token(
    sub="test_hr_user",
    role="HR_ADMIN",
    jti=None,
    expires_in=60,
    token_type="sso_exchange",
    issuer="hrms",
    audience="haven",
    secret=SECRET
):
    now = int(time.time())
    payload = {
        "sub": sub,
        "username": sub,
        "role": role,
        "jti": jti or str(uuid.uuid4()),
        "type": token_type,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + expires_in
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def test_sso_exchange_valid_hr_admin(client):
    token = make_token(sub="hr_director", role="HR_ADMIN")
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Use the returned Haven JWT to access directory
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    dir_res = client.get("/api/v1/employees/directory", headers=headers)
    assert dir_res.status_code == 200

def test_sso_exchange_valid_manager(client):
    token = make_token(sub="engineering_manager", role="MANAGER")
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_sso_exchange_expired_token(client):
    # Expired 30 seconds ago
    token = make_token(sub="hr_user", role="HR_ADMIN", expires_in=-30)
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": token})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

def test_sso_exchange_reused_token(client):
    token = make_token(sub="one_time_user", role="HR_ADMIN")
    # First exchange succeeds
    res1 = client.post("/api/v1/auth/exchange", json={"exchange_token": token})
    assert res1.status_code == 200

    # Second exchange with identical token/jti must be rejected
    res2 = client.post("/api/v1/auth/exchange", json={"exchange_token": token})
    assert res2.status_code == 401
    assert "already been used" in res2.json()["detail"].lower()

def test_sso_exchange_malformed_token(client):
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": "not.a.valid.jwt.token"})
    assert response.status_code == 401
    assert "invalid or malformed" in response.json()["detail"].lower()

def test_sso_exchange_invalid_signature(client):
    wrong_secret_token = make_token(secret="wrong_unshared_secret_key")
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": wrong_secret_token})
    assert response.status_code == 401
    assert "invalid or malformed" in response.json()["detail"].lower()

def test_sso_exchange_invalid_issuer_audience(client):
    bad_iss = make_token(issuer="fraud_system")
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": bad_iss})
    assert response.status_code == 401

    bad_aud = make_token(audience="other_service")
    response2 = client.post("/api/v1/auth/exchange", json={"exchange_token": bad_aud})
    assert response2.status_code == 401

def test_sso_exchange_unauthorized_role(client):
    # Non-HR employee role must be rejected
    token = make_token(sub="regular_employee", role="EMPLOYEE")
    response = client.post("/api/v1/auth/exchange", json={"exchange_token": token})
    assert response.status_code == 403
    assert "not an approved hr role" in response.json()["detail"].lower()

def test_standalone_haven_login_fallback(client):
    # Ensure normal Haven username/password authentication continues to work
    # Register a test admin
    reg = client.post("/api/v1/auth/register", json={
        "username": "standalone_admin",
        "password": "Password123!",
        "role": "HR_ADMIN",
        "is_active": True
    })
    assert reg.status_code == 200

    # Normal OAuth2 password token flow
    login_res = client.post("/api/v1/auth/token", data={
        "username": "standalone_admin",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
