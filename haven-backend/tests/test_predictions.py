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

client = TestClient(app)

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
