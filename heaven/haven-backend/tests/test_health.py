from app.config import get_settings

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

from app.main import app
from app.security.dependencies import get_current_user
from app.database.models import User, RoleEnum

def test_readiness_check(client):
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username="admin", role=RoleEnum.HR_ADMIN)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "error"]
    assert response.json()["database"] == "ok"
    assert response.json()["model"] in ["ok", "unavailable"]
