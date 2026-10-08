import pytest
import os
from app.services.model_service import ModelService

def check_artifacts_exist():
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    return (
        os.path.exists(os.path.join(base, "random_forest_pipeline.joblib")) and
        os.path.exists(os.path.join(base, "random_forest_metadata.json")) and
        os.path.exists(os.path.join(base, "feature_columns.json"))
    )

@pytest.mark.skipif(not check_artifacts_exist(), reason="Real model artifacts are missing. Skipping integration test.")
def test_real_model_integration():
    service = ModelService.get_instance()
    
    assert service.is_available() is True
    
    assert service._metadata.get("target") == "burnout_risk"
    
    assert isinstance(service._feature_columns, list)
    assert "employee_hash" not in service._feature_columns
    
    metrics = {
        "employee_hash": "hash123",
        "week_start_date": "2023-10-01",
        "department": "Engineering"
    }
    
    predicted_class, prob_dict, model_type, model_version = service.predict(metrics)
    
    assert predicted_class in ["Low", "Medium", "High"]
    assert set(prob_dict.keys()) == {"Low", "Medium", "High"}
