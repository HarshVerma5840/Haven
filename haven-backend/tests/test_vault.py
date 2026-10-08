import pytest
from fastapi.testclient import TestClient
from datetime import date

from app.main import app
from app.database.connection import SessionLocal
from app.database.models import User, RoleEnum, IdentityMapping, WeeklyEmployeeMetrics
from app.security.jwt import create_access_token
from app.security.password import get_password_hash

@pytest.fixture
def setup_users(db_session):
    # Create HR Admin
    hr_admin = User(username="vault_admin", password_hash=get_password_hash("password"), role=RoleEnum.HR_ADMIN)
    
    # Create Employees
    employee1 = User(username="emp_sales", password_hash=get_password_hash("password"), role=RoleEnum.EMPLOYEE, employee_hash="hash_sales", department="Sales")
    employee2 = User(username="emp_eng", password_hash=get_password_hash("password"), role=RoleEnum.EMPLOYEE, employee_hash="hash_eng", department="Engineering")
    
    # Create Managers
    manager_sales = User(username="mgr_sales", password_hash=get_password_hash("password"), role=RoleEnum.MANAGER, department="Sales")
    manager_eng = User(username="mgr_eng", password_hash=get_password_hash("password"), role=RoleEnum.MANAGER, department="Engineering")
    
    # Create Metrics
    metric_sales = WeeklyEmployeeMetrics(employee_hash="hash_sales", week_start_date=date(2026, 10, 5), schema_version="1.0", label_source="test", department="Sales")
    metric_eng = WeeklyEmployeeMetrics(employee_hash="hash_eng", week_start_date=date(2026, 10, 5), schema_version="1.0", label_source="test", department="Engineering")
    
    db_session.add_all([hr_admin, employee1, employee2, manager_sales, manager_eng, metric_sales, metric_eng])
    db_session.commit()
    
    return {
        "hr_admin": hr_admin,
        "emp_sales": employee1,
        "emp_eng": employee2,
        "mgr_sales": manager_sales,
        "mgr_eng": manager_eng
    }

@pytest.fixture
def tokens(setup_users):
    return {k: create_access_token(data={"username": v.username}) for k, v in setup_users.items()}

def test_identity_vault_requires_hr_admin(client, tokens):
    response = client.post(
        "/api/v1/vault/identity",
        headers={"Authorization": f"Bearer {tokens['emp_sales']}"},
        json={"email": "test@example.com"}
    )
    assert response.status_code == 403

def test_manager_cannot_access_identity_vault(client, tokens):
    response = client.post(
        "/api/v1/vault/identity",
        headers={"Authorization": f"Bearer {tokens['mgr_sales']}"},
        json={"email": "mgr_test@example.com"}
    )
    assert response.status_code == 403

def test_identity_vault_create_mapping(client, tokens):
    response = client.post(
        "/api/v1/vault/identity",
        headers={"Authorization": f"Bearer {tokens['hr_admin']}"},
        json={"email": "test@example.com", "github_username": "octocat"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["github_username"] == "octocat"
    assert "employee_hash" in data

def test_duplicate_identity_mapping_rejected(client, tokens):
    response1 = client.post(
        "/api/v1/vault/identity",
        headers={"Authorization": f"Bearer {tokens['hr_admin']}"},
        json={"email": "duplicate@example.com"}
    )
    assert response1.status_code == 200
    
    response2 = client.post(
        "/api/v1/vault/identity",
        headers={"Authorization": f"Bearer {tokens['hr_admin']}"},
        json={"email": "duplicate@example.com"}
    )
    assert response2.status_code == 400

def test_missing_vault_data_returns_safe_errors(client, tokens):
    response = client.post(
        "/api/v1/vault/identity",
        headers={"Authorization": f"Bearer {tokens['hr_admin']}"},
        json={} # Missing identifiers
    )
    assert response.status_code == 400

def test_analytical_vault_save_prediction(client, tokens):
    response = client.post(
        "/api/v1/vault/behavioral/predictions",
        headers={"Authorization": f"Bearer {tokens['hr_admin']}"},
        json={
            "employee_hash": "hash_sales",
            "week_start_date": "2026-10-05",
            "burnout_risk": "High",
            "probability_low": 0.1,
            "probability_medium": 0.2,
            "probability_high": 0.7,
            "shap_explanations": '{"feature1": 0.5}',
            "model_version": "v1.0"
        }
    )
    assert response.status_code == 200

def test_analytical_vault_employee_access_own(client, tokens):
    response = client.get(
        "/api/v1/vault/behavioral/predictions/hash_sales",
        headers={"Authorization": f"Bearer {tokens['emp_sales']}"}
    )
    assert response.status_code == 200

def test_analytical_vault_employee_access_other(client, tokens):
    response = client.get(
        "/api/v1/vault/behavioral/predictions/hash_eng",
        headers={"Authorization": f"Bearer {tokens['emp_sales']}"}
    )
    assert response.status_code == 403

def test_manager_access_authorized_behavioral_records(client, tokens):
    response = client.get(
        "/api/v1/vault/behavioral/predictions/hash_sales",
        headers={"Authorization": f"Bearer {tokens['mgr_sales']}"}
    )
    assert response.status_code == 200

def test_manager_cannot_access_unauthorized_behavioral_records(client, tokens):
    response = client.get(
        "/api/v1/vault/behavioral/predictions/hash_eng",
        headers={"Authorization": f"Bearer {tokens['mgr_sales']}"}
    )
    assert response.status_code == 403

def test_hr_admin_can_access_aggregate(client, tokens):
    response = client.get(
        "/api/v1/vault/behavioral/predictions/hash_eng",
        headers={"Authorization": f"Bearer {tokens['hr_admin']}"}
    )
    assert response.status_code == 200
