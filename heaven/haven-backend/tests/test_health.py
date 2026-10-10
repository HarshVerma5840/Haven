import pytest
from unittest.mock import MagicMock
from app.config import get_settings
from app.main import app
from app.security.dependencies import get_current_user
from app.database.models import User, RoleEnum
from app.services.model_service import ModelService

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness_check_model_ok_when_loaded(client):
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username="admin", role=RoleEnum.HR_ADMIN)

    # Ensure real model is loaded
    service = ModelService.get_instance()
    assert service.is_available() is True

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["model"] == "ok"
    assert data["model_name"] == "RandomForestClassifier"
    assert data["model_version"] == "rf-dev-1.1"
    assert data["model_error"] is None

def test_readiness_check_model_unavailable_when_missing(client, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username="admin", role=RoleEnum.HR_ADMIN)

    # Mock unavailable service
    mock_service = MagicMock()
    mock_service.is_available.return_value = False
    mock_service.get_model_name.return_value = "RandomForestClassifier"
    mock_service.get_model_version.return_value = None
    mock_service.get_load_error.return_value = "Missing required model artifact(s) in /models: random_forest_pipeline.joblib"

    monkeypatch.setattr(ModelService, "get_instance", lambda: mock_service)

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["database"] == "ok"
    assert data["model"] == "unavailable"
    assert data["model_name"] == "RandomForestClassifier"
    assert "Missing required model artifact(s)" in data["model_error"]

def test_readiness_model_ok_only_when_actually_loaded(client, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username="admin", role=RoleEnum.HR_ADMIN)

    # Verify that if is_available() is False, model is NEVER "ok"
    mock_service = MagicMock()
    mock_service.is_available.return_value = False
    mock_service.get_model_name.return_value = "RandomForestClassifier"
    mock_service.get_load_error.return_value = "Failed to load model artifacts"

    monkeypatch.setattr(ModelService, "get_instance", lambda: mock_service)

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] != "ok"
    assert data["model"] == "unavailable"
