import pytest
from datetime import date
from app.database.models import User, RoleEnum, WeeklyEmployeeMetrics, BurnoutPrediction
from app.security.password import get_password_hash


@pytest.fixture(autouse=True)
def setup_directory_data(db_session):
    # Setup users
    db_session.query(User).delete()
    db_session.add(User(username="hr_admin", password_hash=get_password_hash("pass"), role=RoleEnum.HR_ADMIN))
    db_session.add(User(username="eng_manager", password_hash=get_password_hash("pass"), role=RoleEnum.MANAGER, department="Engineering"))
    db_session.add(User(username="emp_user", password_hash=get_password_hash("pass"), role=RoleEnum.EMPLOYEE, employee_hash="emp_hash_1"))
    db_session.commit()

    # Setup behavioral metrics in behavioral session
    behav = db_session.behav
    behav.query(WeeklyEmployeeMetrics).delete()
    behav.query(BurnoutPrediction).delete()

    behav.add(WeeklyEmployeeMetrics(
        employee_hash="emp_hash_1",
        week_start_date=date(2026, 10, 2),
        department="Engineering",
        designation="Software Engineer",
        burnout_risk="High",
        schema_version="1.0",
        label_source="hrms",
        data_completeness=98.0
    ))
    behav.add(WeeklyEmployeeMetrics(
        employee_hash="emp_hash_2",
        week_start_date=date(2026, 10, 2),
        department="Sales",
        designation="Account Executive",
        burnout_risk="Low",
        schema_version="1.0",
        label_source="hrms",
        data_completeness=92.0
    ))
    behav.add(WeeklyEmployeeMetrics(
        employee_hash="emp_hash_3",
        week_start_date=date(2026, 10, 2),
        department="Engineering",
        designation="QA Lead",
        burnout_risk="Medium",
        schema_version="1.0",
        label_source="hrms",
        data_completeness=95.0
    ))

    # Add predictions
    behav.add(BurnoutPrediction(
        employee_hash="emp_hash_1",
        week_start_date=date(2026, 10, 2),
        predicted_risk="High",
        low_probability=0.05,
        medium_probability=0.15,
        high_probability=0.80,
        model_type="catboost",
        model_version="v1.2.0-prod"
    ))
    behav.add(BurnoutPrediction(
        employee_hash="emp_hash_3",
        week_start_date=date(2026, 10, 2),
        predicted_risk="Medium",
        low_probability=0.20,
        medium_probability=0.60,
        high_probability=0.20,
        model_type="catboost",
        model_version="v1.2.0-prod"
    ))
    behav.commit()
    yield


def get_token(client, username):
    res = client.post("/api/v1/auth/token", data={"username": username, "password": "pass"})
    return res.json()["access_token"]


def test_directory_unauthenticated(client):
    res = client.get("/api/v1/employees/directory")
    assert res.status_code == 401


def test_directory_employee_forbidden(client):
    token = get_token(client, "emp_user")
    res = client.get("/api/v1/employees/directory", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "Requires MANAGER or HR_ADMIN role" in res.json()["detail"]


def test_directory_hr_admin_access(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/employees/directory", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Check fields of each item
    for item in data["items"]:
        assert "employee_hash" in item
        assert "department" in item
        assert "designation" in item
        assert "current_burnout_risk" in item
        assert "prediction_date" in item
        assert "model_version" in item
        assert "data_completeness" in item

        # Verify identity vault fields are NEVER exposed
        assert "email" not in item
        assert "github_username" not in item
        assert "hrms_employee_id" not in item
        assert "password" not in item
        assert "password_hash" not in item


def test_directory_manager_department_scoping(client):
    token = get_token(client, "eng_manager")
    res = client.get("/api/v1/employees/directory", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    # Manager of Engineering should only see Engineering records (emp_hash_1 and emp_hash_3)
    assert data["total"] == 2
    for item in data["items"]:
        assert item["department"] == "Engineering"


def test_directory_search_filter(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/employees/directory?search=Account", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["designation"] == "Account Executive"


def test_directory_risk_filter(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/employees/directory?risk=High", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["employee_hash"] == "emp_hash_1"
    assert data["items"][0]["current_burnout_risk"] == "High"


def test_directory_sorting(client):
    token = get_token(client, "hr_admin")
    # Sort High -> Low
    res = client.get("/api/v1/employees/directory?sort_by=risk_desc", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    items = res.json()["items"]
    risks = [it["current_burnout_risk"] for it in items]
    assert risks[0] == "High"


def test_directory_pagination(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/employees/directory?page=1&page_size=2", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2
    assert data["page"] == 1
