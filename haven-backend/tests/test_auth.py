import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.models import User, RoleEnum
from app.security.password import get_password_hash
from app.api.predictions import get_model_service
from app.services.model_service import ModelService
from unittest.mock import MagicMock
from app.main import app

@pytest.fixture(autouse=True)
def setup_users(db_session):
    db_session.query(User).delete()
    db_session.add(User(username="hr", password_hash=get_password_hash("pass"), role=RoleEnum.HR_ADMIN))
    db_session.add(User(username="mgr1", password_hash=get_password_hash("pass"), role=RoleEnum.MANAGER, department="Engineering"))
    db_session.add(User(username="emp1", password_hash=get_password_hash("pass"), role=RoleEnum.EMPLOYEE, employee_hash="hash1", department="Engineering"))
    db_session.add(User(username="emp2", password_hash=get_password_hash("pass"), role=RoleEnum.EMPLOYEE, employee_hash="hash2", department="Sales"))
    db_session.add(User(username="inactive_emp", password_hash=get_password_hash("pass"), role=RoleEnum.EMPLOYEE, employee_hash="hash3", is_active=False))
    db_session.commit()
    
    # Also add WeeklyEmployeeMetrics for manager RBAC testing
    from app.database.models import WeeklyEmployeeMetrics
    from datetime import date
    db_session.behav.add(WeeklyEmployeeMetrics(employee_hash="hash1", department="Engineering", week_start_date=date(2023, 10, 1), schema_version="1", label_source="test"))
    db_session.behav.add(WeeklyEmployeeMetrics(employee_hash="hash2", department="Sales", week_start_date=date(2023, 10, 1), schema_version="1", label_source="test"))
    db_session.behav.commit()
    
    yield


def test_login_success(client):
    response = client.post("/api/v1/auth/token", data={"username": "hr", "password": "pass"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure(client):
    response = client.post("/api/v1/auth/token", data={"username": "hr", "password": "wrong"})
    assert response.status_code == 401

def test_login_inactive(client):
    response = client.post("/api/v1/auth/token", data={"username": "inactive_emp", "password": "pass"})
    assert response.status_code == 403
    assert "Inactive user account" in response.json()["detail"]

def test_login_unknown_user(client):
    response = client.post("/api/v1/auth/token", data={"username": "nobody", "password": "pass"})
    assert response.status_code == 401

def test_missing_auth_header(client):
    response = client.get("/ready")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

def test_malformed_jwt(client):
    response = client.get("/ready", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

def test_expired_jwt(client):
    from app.security.jwt import create_access_token
    from datetime import timedelta
    expired_token = create_access_token(data={"username": "hr"}, expires_delta=timedelta(minutes=-10))
    response = client.get("/ready", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert "Token has expired" in response.json()["detail"]


def test_rbac_employee_success(client):
    # Login as emp1
    token = client.post("/api/v1/auth/token", data={"username": "emp1", "password": "pass"}).json()["access_token"]
    
    # Mock model service
    service = MagicMock(spec=ModelService)
    service.is_available.return_value = True
    service.predict.return_value = ("Low", {"Low": 0.8, "Medium": 0.1, "High": 0.1}, "RF", "1.0")
    app.dependency_overrides[get_model_service] = lambda: service
    
    # Emp1 asks for emp1's prediction
    payload = {"metrics": {"employee_hash": "hash1", "week_start_date": "2023-10-01", "department": "Sales"}}
    res = client.post("/api/v1/predictions", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    
    app.dependency_overrides.clear()

def test_rbac_employee_failure(client):
    # Login as emp1
    token = client.post("/api/v1/auth/token", data={"username": "emp1", "password": "pass"}).json()["access_token"]
    
    # Emp1 asks for emp2's prediction
    payload = {"metrics": {"employee_hash": "hash2", "week_start_date": "2023-10-01", "department": "Sales"}}
    res = client.post("/api/v1/predictions", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "their own records" in res.json()["detail"]

def test_rbac_manager_success(client):
    token = client.post("/api/v1/auth/token", data={"username": "mgr1", "password": "pass"}).json()["access_token"]
    
    service = MagicMock(spec=ModelService)
    service.is_available.return_value = True
    service.predict.return_value = ("Low", {"Low": 0.8, "Medium": 0.1, "High": 0.1}, "RF", "1.0")
    app.dependency_overrides[get_model_service] = lambda: service
    
    payload = {"metrics": {"employee_hash": "hash1", "week_start_date": "2023-10-01", "department": "Engineering"}}
    res = client.post("/api/v1/predictions", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    
    app.dependency_overrides.clear()

def test_rbac_manager_failure(client):
    token = client.post("/api/v1/auth/token", data={"username": "mgr1", "password": "pass"}).json()["access_token"]
    
    # Manager tries to access Sales employee but spoofs the department in payload to match their own
    payload = {"metrics": {"employee_hash": "hash2", "week_start_date": "2023-10-01", "department": "Engineering"}}
    res = client.post("/api/v1/predictions", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "their department" in res.json()["detail"]

def test_rbac_hr_admin_success(client):
    token = client.post("/api/v1/auth/token", data={"username": "hr", "password": "pass"}).json()["access_token"]
    
    # HR_ADMIN hits prediction route
    service = MagicMock(spec=ModelService)
    service.is_available.return_value = True
    service.predict.return_value = ("Low", {"Low": 0.8, "Medium": 0.1, "High": 0.1}, "RF", "1.0")
    app.dependency_overrides[get_model_service] = lambda: service
    
    payload = {"metrics": {"employee_hash": "hash_any", "week_start_date": "2023-10-01", "department": "Any"}}
    res = client.post("/api/v1/predictions", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    
    app.dependency_overrides.clear()

def test_hr_admin_analytics_access(client):
    token = client.post("/api/v1/auth/token", data={"username": "hr", "password": "pass"}).json()["access_token"]
    res = client.get("/api/v1/analytics/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

def test_manager_analytics_rejected(client):
    token = client.post("/api/v1/auth/token", data={"username": "mgr1", "password": "pass"}).json()["access_token"]
    res = client.get("/api/v1/analytics/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

def test_privileged_routes_persist_after_restart(client):
    # This test verifies that the secret key is static and tokens survive server restarts
    # by generating a token and verifying it directly against the app config.
    from app.config import get_settings
    from app.security.jwt import create_access_token
    import importlib
    import app.config
    
    settings = get_settings()
    token = create_access_token(data={"username": "hr"})
    
    # Simulate restart by reloading config
    importlib.reload(app.config)
    new_settings = app.config.get_settings()
    
    assert settings.jwt_secret == new_settings.jwt_secret
    assert settings.jwt_secret != "random", "JWT secret should be statically defined for persistence"
    
    res = client.get("/api/v1/analytics/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
