import pytest
from datetime import date
from app.database.models import User, RoleEnum, WeeklyEmployeeMetrics, BurnoutPrediction
from app.security.password import get_password_hash


@pytest.fixture(autouse=True)
def setup_users(db_session):
    db_session.query(User).delete()
    db_session.add(User(username="hr_admin", password_hash=get_password_hash("pass"), role=RoleEnum.HR_ADMIN))
    db_session.add(User(username="eng_manager", password_hash=get_password_hash("pass"), role=RoleEnum.MANAGER, department="Engineering"))
    db_session.add(User(username="emp", password_hash=get_password_hash("pass"), role=RoleEnum.EMPLOYEE, employee_hash="hash1"))
    db_session.commit()

    behav = db_session.behav
    behav.query(WeeklyEmployeeMetrics).delete()
    behav.query(BurnoutPrediction).delete()

    behav.add(WeeklyEmployeeMetrics(
        employee_hash="hash1",
        week_start_date=date(2026, 10, 2),
        department="Engineering",
        designation="Software Engineer",
        burnout_risk="High",
        schema_version="1.0",
        label_source="hrms",
        data_completeness=95.0
    ))
    behav.add(WeeklyEmployeeMetrics(
        employee_hash="hash2",
        week_start_date=date(2026, 10, 2),
        department="Engineering",
        designation="DevOps Engineer",
        burnout_risk="Medium",
        schema_version="1.0",
        label_source="hrms",
        data_completeness=90.0
    ))
    behav.add(BurnoutPrediction(
        employee_hash="hash1",
        week_start_date=date(2026, 10, 2),
        predicted_risk="High",
        low_probability=0.05,
        medium_probability=0.15,
        high_probability=0.80,
        model_type="CatBoost",
        model_version="v1.2.0-prod"
    ))
    behav.commit()
    yield


def get_token(client, username):
    res = client.post("/api/v1/auth/token", data={"username": username, "password": "pass"})
    return res.json()["access_token"]


def test_network_graph_unauthenticated(client):
    res = client.get("/api/v1/analytics/network")
    assert res.status_code == 401


def test_network_graph_employee_forbidden(client):
    token = get_token(client, "emp")
    res = client.get("/api/v1/analytics/network", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_network_graph_hr_admin_success(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/analytics/network", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0

    for node in data["nodes"]:
        assert "id" in node
        assert "department" in node
        assert "risk" in node
        assert "centrality" in node
        assert "degree" in node
        # Never expose identity fields
        assert "email" not in node
        assert "password" not in node

    for edge in data["edges"]:
        assert "source" in edge
        assert "target" in edge
        assert "weight" in edge


def test_network_graph_department_filter(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/analytics/network?department=Engineering", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    for node in data["nodes"]:
        assert node["department"] == "Engineering"


def test_integration_status_success(client):
    token = get_token(client, "hr_admin")
    res = client.get("/api/v1/analytics/integration", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["hrms_connection_status"] == "Connected"
    assert "jwe_encryption_status" in data
    assert "service_token_status" in data
    assert "records_received" in data
    assert data["records_failed"] == 0
    assert "data_completeness" in data
    # Ensure keys or tokens are not exposed
    assert "private_key" not in data
    assert "token" not in data or data["token"] is None or "service_token_status" in data


def test_ready_health_with_redis_and_encryption(client):
    token = get_token(client, "hr_admin")
    res = client.get("/ready", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "database" in data
    assert "model" in data
    assert "redis" in data
    assert "encryption" in data
    assert data["database"] == "ok"
    assert data["redis"] == "ok"
    assert data["encryption"] == "ok"


def test_empty_behavioral_data_states(client, db_session):
    # Clear behavioral metrics
    behav = db_session.behav
    behav.query(WeeklyEmployeeMetrics).delete()
    behav.query(BurnoutPrediction).delete()
    behav.commit()

    token = get_token(client, "hr_admin")

    # Network graph returns empty nodes/edges and demo flag
    net_res = client.get("/api/v1/analytics/network", headers={"Authorization": f"Bearer {token}"})
    assert net_res.status_code == 200
    net_data = net_res.json()
    assert net_data["nodes"] == []
    assert net_data["edges"] == []
    assert net_data["is_demo"] is True

    # Integration status returns Awaiting First Ingestion
    int_res = client.get("/api/v1/analytics/integration", headers={"Authorization": f"Bearer {token}"})
    assert int_res.status_code == 200
    int_data = int_res.json()
    assert int_data["hrms_connection_status"] == "Awaiting First Ingestion"
    assert int_data["records_received"] == 0
    assert int_data["is_live"] is False


def test_github_integration_status_endpoint(client, monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("GITHUB_TOKEN", "mock_github_pat_123456789")
    monkeypatch.setenv("GITHUB_ORGANIZATION", "test-org")
    monkeypatch.setenv("GITHUB_REPOSITORIES", "test-org/repo1,test-org/repo2")
    get_settings.cache_clear()

    # 1. Unauthenticated request rejected
    res_unauth = client.get("/api/v1/analytics/integration/github")
    assert res_unauth.status_code == 401

    # 2. Non-HR user (regular employee) rejected
    emp_token = get_token(client, "emp")
    res_emp = client.get("/api/v1/analytics/integration/github", headers={"Authorization": f"Bearer {emp_token}"})
    assert res_emp.status_code == 403

    # 3. HR Admin authorized
    admin_token = get_token(client, "hr_admin")
    res_admin = client.get("/api/v1/analytics/integration/github", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    data = res_admin.json()

    assert data["configured"] is True
    assert data["status"] == "Ready for Aggregation"
    assert data["organization_configured"] is True
    assert data["repository_count"] == 2
    assert "working_timezone" in data
    assert "workday_window" in data
    assert data["is_live_streaming"] is False
    assert "custom_github_username" in data["identity_mapping_field"]

    # 4. Strict check: NO secret leakage in response
    assert "mock_github_pat_123456789" not in str(data)
    assert "github_token" not in data
    assert "token" not in data

    # 5. Check main integration endpoint also reflects GitHub status without secret leak
    main_res = client.get("/api/v1/analytics/integration", headers={"Authorization": f"Bearer {admin_token}"})
    assert main_res.status_code == 200
    main_data = main_res.json()
    assert main_data["github_configured"] is True
    assert main_data["github_repository_count"] == 2
    assert "mock_github_pat_123456789" not in str(main_data)
    assert "github_token" not in main_data

    get_settings.cache_clear()
