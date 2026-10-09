import os
import json
import joblib
import pytest
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier

from app.services.shap_service import ShapService, ShapServiceError

@pytest.fixture
def mock_shap_artifacts(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    # 1. Create a minimal dataframe
    df = pd.DataFrame({
        "department": ["Engineering", "Sales", "Engineering", "HR", "Sales"],
        "avg_daily_work_hours": [8.5, 9.0, 7.5, 8.0, 10.0],
        "burnout_risk": ["Low", "Medium", "Low", "Medium", "High"]
    })
    
    X = df[["department", "avg_daily_work_hours"]]
    y = df["burnout_risk"]
    
    # 2. Build Pipeline
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='mean'))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('numeric', numeric_transformer, ["avg_daily_work_hours"]),
            ('categorical', categorical_transformer, ["department"])
        ]
    )
    
    clf = RandomForestClassifier(n_estimators=10, random_state=42)
    
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', clf)
    ])
    
    # Fit the pipeline
    pipeline.fit(X, y)
    
    # Save artifacts
    pipeline_path = models_dir / "random_forest_pipeline.joblib"
    metadata_path = models_dir / "random_forest_metadata.json"
    features_path = models_dir / "feature_columns.json"
    
    joblib.dump(pipeline, pipeline_path)
    
    with open(metadata_path, "w") as f:
        json.dump({"model_version": "test-1.0", "model_type": "Random Forest"}, f)
        
    with open(features_path, "w") as f:
        json.dump({
            "numeric_columns": ["avg_daily_work_hours"],
            "categorical_columns": ["department"]
        }, f)
        
    return str(pipeline_path), str(metadata_path), str(features_path)

def test_shap_service_loads_correctly(mock_shap_artifacts):
    pipeline_path, metadata_path, features_path = mock_shap_artifacts
    service = ShapService(pipeline_path, metadata_path, features_path)
    
    assert service.is_available() is True
    assert service._model_version == "test-1.0"
    assert service._explainer is not None

def test_shap_explanation_output(mock_shap_artifacts):
    pipeline_path, metadata_path, features_path = mock_shap_artifacts
    service = ShapService(pipeline_path, metadata_path, features_path)
    
    metrics = {
        "employee_hash": "secret123",
        "department": "Engineering",
        "avg_daily_work_hours": 9.5
    }
    
    explanation = service.explain(metrics)
    
    # Check output structure
    assert explanation["model_version"] == "test-1.0"
    assert "not causal explanations" in explanation["disclaimer"]
    
    exps = explanation["explanations"]
    assert "Low" in exps
    assert "Medium" in exps
    assert "High" in exps
    
    # Check that it's non-empty and directions are correct
    for cls_name, cls_exp in exps.items():
        assert "top_positive" in cls_exp
        assert "top_negative" in cls_exp
        
        for item in cls_exp["top_positive"]:
            assert item["contribution"] > 0
            assert item["direction"] == "positive"
            assert "increases" in item["description"]
            
        for item in cls_exp["top_negative"]:
            assert item["contribution"] < 0
            assert item["direction"] == "negative"
            assert "decreases" in item["description"]

def test_identity_fields_never_appear(mock_shap_artifacts):
    pipeline_path, metadata_path, features_path = mock_shap_artifacts
    service = ShapService(pipeline_path, metadata_path, features_path)
    
    metrics = {
        "employee_hash": "secret123",
        "email": "test@example.com",
        "github_username": "testuser",
        "hrms_employee_id": "EMP001",
        "department": "Engineering",
        "avg_daily_work_hours": 9.5
    }
    
    explanation = service.explain(metrics)
    exps = explanation["explanations"]
    
    for cls_name, cls_exp in exps.items():
        for lst in [cls_exp["top_positive"], cls_exp["top_negative"]]:
            for item in lst:
                feat = item["feature"]
                assert "employee_hash" not in feat
                assert "email" not in feat
                assert "github_username" not in feat
                assert "hrms_employee_id" not in feat

def test_unknown_categorical_values(mock_shap_artifacts):
    pipeline_path, metadata_path, features_path = mock_shap_artifacts
    service = ShapService(pipeline_path, metadata_path, features_path)
    
    metrics = {
        "department": "Marketing_Unknown",
        "avg_daily_work_hours": 9.5
    }
    
    # Should not raise exception
    explanation = service.explain(metrics)
    assert explanation is not None

def test_shap_service_unavailable(tmp_path):
    # Pass non-existent paths
    service = ShapService(
        str(tmp_path / "non_existent.joblib"),
        str(tmp_path / "non_existent.json"),
        str(tmp_path / "non_existent.json")
    )
    
    assert service.is_available() is False
    with pytest.raises(ShapServiceError, match="SHAP service is not available"):
        service.explain({"avg_daily_work_hours": 9.5})
