from app.config import get_settings

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] in ["ok", "error"]
    assert response.json()["database"] == "ok"
    assert response.json()["model"] in ["ok", "unavailable"]
