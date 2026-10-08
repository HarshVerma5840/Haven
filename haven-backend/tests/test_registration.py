import pytest
from app.database.models import User, RoleEnum
from app.security.password import get_password_hash

@pytest.fixture(autouse=True)
def setup_users(db_session):
    db_session.query(User).delete()
    db_session.add(User(username="hr", password_hash=get_password_hash("pass"), role=RoleEnum.HR_ADMIN))
    db_session.add(User(username="emp1", password_hash=get_password_hash("pass"), role=RoleEnum.EMPLOYEE, employee_hash="hash1", department="Engineering"))
    db_session.commit()
    yield

def test_public_registration_prevents_privilege_escalation(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "hacker",
        "password": "password",
        "role": "HR_ADMIN"
    })
    assert response.status_code == 403
    assert "restricted to the EMPLOYEE role" in response.json()["detail"]

def test_public_registration_allows_employee(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "new_emp",
        "password": "password",
        "role": "EMPLOYEE",
        "employee_hash": "hash_new"
    })
    assert response.status_code == 200
    assert response.json()["username"] == "new_emp"

def test_hr_admin_can_create_manager(client):
    # Login as hr_admin
    token_response = client.post("/api/v1/auth/token", data={"username": "hr", "password": "pass"})
    token = token_response.json()["access_token"]
    
    response = client.post("/api/v1/auth/users", 
        json={
            "username": "new_mgr",
            "password": "password",
            "role": "MANAGER",
            "department": "Engineering"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "new_mgr"

def test_employee_cannot_create_users(client):
    # Login as emp1
    token_response = client.post("/api/v1/auth/token", data={"username": "emp1", "password": "pass"})
    token = token_response.json()["access_token"]
    
    response = client.post("/api/v1/auth/users", 
        json={
            "username": "new_mgr_hack",
            "password": "password",
            "role": "MANAGER",
            "department": "Engineering"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

def test_duplicate_username_handling(client):
    # Register emp
    client.post("/api/v1/auth/register", json={
        "username": "duplicate_user",
        "password": "password",
        "role": "EMPLOYEE"
    })
    
    # Try again
    response = client.post("/api/v1/auth/register", json={
        "username": "duplicate_user",
        "password": "password",
        "role": "EMPLOYEE"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]
