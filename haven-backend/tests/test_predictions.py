import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import json
import os
import pandas as pd

from app.main import app
from app.api.predictions import get_model_service
from app.services.model_service import ModelService, ModelNotAvailableError
from app.schemas.metrics import WeeklyEmployeeMetricsInput
from app.security.dependencies import get_current_user
from app.database.models import User, RoleEnum

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_auth():
    def mock_get_current_user():
        return User(id=1, username="admin", role=RoleEnum.HR_ADMIN)
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def mock_artifacts(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    meta = {"version": "1.0", "model_type": "Random Forest"}
    with open(models_dir / "random_forest_metadata.json", "w") as f:
        json.dump(meta, f)

    features = ["department", "avg_daily_work_hours", "github_commit_count"]
    with open(models_dir / "feature_columns.json", "w") as f:
        json.dump(features, f)

    pipeline_path = models_dir / "random_forest_pipeline.joblib"
    pipeline_path.touch()

    return str(models_dir)

@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock()
    # Mocking probability values to ensure they are bounded 0..1
    pipeline.predict_proba.return_value = [[0.2, 0.7, 0.1]]
    pipeline.classes_ = ["Low", "Medium", "High"]
    return pipeline

def test_successful_model_loading_injection(mock_pipeline):
    """Test loading with the canonical object-form feature metadata."""
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy",
        injected_pipeline=mock_pipeline,
        injected_metadata={"model_version": "2.0", "model_type": "Random Forest"},
        injected_features={
            "numeric_columns": ["avg_daily_work_hours", "github_commit_count"],
            "categorical_columns": ["department"],
            "target": "burnout_risk",
            "identifier_column": "employee_hash"
        }
    )

    assert service.is_available() is True
    assert service._metadata["model_version"] == "2.0"
    assert service._feature_columns == ["avg_daily_work_hours", "github_commit_count", "department"]

def test_legacy_list_feature_metadata(mock_pipeline):
    """Test loading with the legacy list-form feature metadata."""
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy",
        injected_pipeline=mock_pipeline,
        injected_metadata={"model_version": "1.0"},
        injected_features=["avg_daily_work_hours", "department"]
    )
    assert service.is_available() is True
    assert service._feature_columns == ["avg_daily_work_hours", "department"]

def test_forbidden_feature_columns_rejected(mock_pipeline):
    with pytest.raises(ValueError) as exc:
        ModelService(
            pipeline_path="dummy",
            metadata_path="dummy",
            features_path="dummy",
            injected_pipeline=mock_pipeline,
            injected_metadata={"model_version": "1.0"},
            injected_features={
                "numeric_columns": ["avg_daily_work_hours"],
                "categorical_columns": ["employee_hash"] # Forbidden
            }
        )
    assert "Forbidden column" in str(exc.value)

def test_missing_feature_columns_rejected(mock_pipeline):
    with pytest.raises(ValueError) as exc:
        ModelService(
            pipeline_path="dummy",
            metadata_path="dummy",
            features_path="dummy",
            injected_pipeline=mock_pipeline,
            injected_metadata={"model_version": "1.0"},
            injected_features={
                "target": "burnout_risk" # Missing arrays
            }
        )
    assert "must contain numeric_columns" in str(exc.value)

def test_missing_artifact(mock_artifacts):
    os.remove(os.path.join(mock_artifacts, "random_forest_metadata.json"))
    service = ModelService(
        pipeline_path=os.path.join(mock_artifacts, "random_forest_pipeline.joblib"),
        metadata_path=os.path.join(mock_artifacts, "random_forest_metadata.json"),
        features_path=os.path.join(mock_artifacts, "feature_columns.json")
    )

    assert service.is_available() is False

def test_invalid_metadata(mock_artifacts):
    with open(os.path.join(mock_artifacts, "random_forest_metadata.json"), "w") as f:
        f.write("{invalid_json}")

    service = ModelService(
        pipeline_path=os.path.join(mock_artifacts, "random_forest_pipeline.joblib"),
        metadata_path=os.path.join(mock_artifacts, "random_forest_metadata.json"),
        features_path=os.path.join(mock_artifacts, "feature_columns.json")
    )

    assert service.is_available() is False # Malformed metadata returns model unavailable

def test_prediction_behavior(mock_pipeline):
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy",
        injected_pipeline=mock_pipeline,
        injected_metadata={"version": "1.0", "model_type": "Random Forest"},
        injected_features=["department", "avg_daily_work_hours", "github_commit_count"]
    )

    metrics = {
        "employee_hash": "hash123",
        "week_start_date": "2023-10-01",
        "department": "Engineering_Unknown", # Unknown categorical value should pass through
        "avg_daily_work_hours": 8.5,
        # missing numeric (github_commit_count)
    }

    predicted_class, prob_dict, model_type, model_version = service.predict(metrics)

    assert predicted_class == "Medium"
    # Low, Medium, High probabilities returned and are between 0 and 1
    assert prob_dict == {"Low": 0.2, "Medium": 0.7, "High": 0.1}
    for prob in prob_dict.values():
        assert 0.0 <= prob <= 1.0

    assert model_type == "Random Forest"
    assert model_version == "1.0"

    df_arg = mock_pipeline.predict_proba.call_args[0][0]
    assert list(df_arg.columns) == ["department", "avg_daily_work_hours", "github_commit_count"]
    assert df_arg.iloc[0]["department"] == "Engineering_Unknown" # categorical passed through for pipeline to handle
    assert df_arg.iloc[0]["avg_daily_work_hours"] == 8.5
    assert pd.isna(df_arg.iloc[0]["github_commit_count"]) # Missing numeric passed as None/NaN

def test_api_success(mock_pipeline):
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy",
        injected_pipeline=mock_pipeline,
        injected_metadata={"version": "1.0", "model_type": "Random Forest"},
        injected_features=["department", "avg_daily_work_hours", "github_commit_count"]
    )
    app.dependency_overrides[get_model_service] = lambda: service

    payload = {
        "metrics": {
            "employee_hash": "hash123",
            "week_start_date": "2023-10-01",
            "department": "Engineering",
            "avg_daily_work_hours": 8.5
        }
    }

    response = client.post("/api/v1/predictions", json=payload)
    app.dependency_overrides.clear()

    assert response.status_code == 200 # Successful response
    data = response.json()
    assert data["predicted_risk"] == "Medium"
    assert data["probabilities"]["Medium"] == 0.7
    # Raw employee_hash/github usernames are not returned
    assert "employee_hash" not in data
    assert "github_username" not in data

def test_api_validation_failure(mock_pipeline):
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy",
        injected_pipeline=mock_pipeline,
        injected_metadata={"version": "1.0"},
        injected_features=["department"]
    )
    app.dependency_overrides[get_model_service] = lambda: service

    # Missing week_start_date
    payload = {
        "metrics": {
            "employee_hash": "hash123",
            "avg_daily_work_hours": 8.5
        }
    }

    response = client.post("/api/v1/predictions", json=payload)
    app.dependency_overrides.clear()
    assert response.status_code == 422 # Invalid prediction request returns HTTP 422

def test_api_model_unavailable():
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy"
    ) # Missing injection and missing files -> becomes unavailable

    app.dependency_overrides[get_model_service] = lambda: service

    payload = {
        "metrics": {
            "employee_hash": "hash123",
            "week_start_date": "2023-10-01",
            "department": "Engineering"
        }
    }

    response = client.post("/api/v1/predictions", json=payload)
    app.dependency_overrides.clear()
    assert response.status_code == 503 # Missing artifacts return HTTP 503
    assert response.json()["detail"] == "Model is currently unavailable."

def test_missing_artifacts_detection_with_specific_filenames(tmp_path):
    empty_dir = tmp_path / "empty_models"
    empty_dir.mkdir()
    service = ModelService(model_dir=str(empty_dir))
    assert service.is_available() is False
    load_err = service.get_load_error()
    assert load_err is not None
    assert "Missing required model artifact(s)" in load_err
    assert "random_forest_pipeline.joblib" in load_err
    assert "random_forest_metadata.json" in load_err
    assert "feature_columns.json" in load_err

def test_invalid_classes_injected_pipeline_rejected():
    mock_bad_pipe = MagicMock()
    mock_bad_pipe.classes_ = ["Low", "Medium"] # Missing "High"
    with pytest.raises(ValueError) as exc:
        ModelService(
            pipeline_path="dummy",
            metadata_path="dummy",
            features_path="dummy",
            injected_pipeline=mock_bad_pipe,
            injected_metadata={"version": "1.0"},
            injected_features=["avg_daily_work_hours"]
        )
    assert "do not contain required classes" in str(exc.value)

class _DummyPipelineWithClasses:
    def __init__(self, classes):
        self.classes_ = classes

def test_invalid_classes_loaded_from_disk(tmp_path):
    import joblib
    models_dir = tmp_path / "models_invalid_classes"
    models_dir.mkdir()

    # Save a pipeline with wrong classes
    bad_pipe = _DummyPipelineWithClasses(["Low", "High"]) # Missing "Medium"
    pipeline_file = models_dir / "random_forest_pipeline.joblib"
    joblib.dump(bad_pipe, pipeline_file)

    meta_file = models_dir / "random_forest_metadata.json"
    meta_file.write_text(json.dumps({"model_version": "1.0", "model_type": "RandomForestClassifier"}))

    features_file = models_dir / "feature_columns.json"
    features_file.write_text(json.dumps(["department", "avg_daily_work_hours"]))

    service = ModelService(model_dir=str(models_dir))
    assert service.is_available() is False
    assert "do not contain required classes" in service.get_load_error()

def test_configurable_model_dir_env(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom_model_dir"
    custom_dir.mkdir()
    monkeypatch.setenv("MODEL_DIR", str(custom_dir))

    resolved = ModelService.resolve_model_dir()
    assert resolved == str(custom_dir.resolve())

def test_prediction_filters_forbidden_columns(mock_pipeline):
    service = ModelService(
        pipeline_path="dummy",
        metadata_path="dummy",
        features_path="dummy",
        injected_pipeline=mock_pipeline,
        injected_metadata={"version": "1.0", "model_type": "RandomForestClassifier"},
        injected_features=["department", "avg_daily_work_hours"]
    )

    metrics = {
        "employee_hash": "secret_emp_123",
        "week_start": "2026-10-01",
        "week_start_date": "2026-10-01",
        "burnout_score": 85.5,
        "burnout_risk": "High",
        "department": "Engineering",
        "avg_daily_work_hours": 9.2
    }

    pred_class, probs, model_name, version = service.predict(metrics)
    assert pred_class == "Medium"
    assert model_name == "RandomForestClassifier"

    # Verify DataFrame passed to pipeline has only ordered features from feature_columns.json
    df_arg = mock_pipeline.predict_proba.call_args[0][0]
    assert list(df_arg.columns) == ["department", "avg_daily_work_hours"]
    assert "employee_hash" not in df_arg.columns
    assert "week_start" not in df_arg.columns
    assert "burnout_score" not in df_arg.columns
    assert "burnout_risk" not in df_arg.columns
