import os
import pytest
import pandas as pd

from data.generate_synthetic_dataset import generate_synthetic_dataset
from ml.data_loader import load_and_preprocess_data
from ml.train_baseline import train_and_save_baseline

@pytest.fixture
def synthetic_csv(tmp_path):
    output_path = str(tmp_path / "test_synthetic.csv")
    generate_synthetic_dataset(output_path, num_employees=10, num_weeks=5, seed=123)
    return output_path

def test_reproducible_generation(tmp_path):
    out1 = str(tmp_path / "1.csv")
    out2 = str(tmp_path / "2.csv")
    
    generate_synthetic_dataset(out1, num_employees=5, num_weeks=2, seed=99)
    generate_synthetic_dataset(out2, num_employees=5, num_weeks=2, seed=99)
    
    df1 = pd.read_csv(out1)
    df2 = pd.read_csv(out2)
    
    pd.testing.assert_frame_equal(df1, df2)

def test_generation_correct_row_count_and_keys(synthetic_csv):
    df = pd.read_csv(synthetic_csv)
    
    # 10 employees * 5 weeks = 50 rows
    assert len(df) == 50
    
    # Unique keys
    assert df.duplicated(subset=["employee_hash", "week_start_date"]).sum() == 0

def test_valid_schema_in_generation(synthetic_csv):
    df = pd.read_csv(synthetic_csv)
    
    assert "burnout_score" in df.columns
    assert "label_source" in df.columns
    
    assert all(df["label_source"] == "synthetic")
    assert all((df["burnout_score"] >= 0.0) & (df["burnout_score"] <= 1.0))
    assert set(df["burnout_risk"].unique()).issubset({"Low", "Medium", "High"})

def test_no_leaked_identifiers_in_features(synthetic_csv):
    X, y = load_and_preprocess_data(synthetic_csv)
    
    forbidden_substrings = ["hash", "date", "timestamp", "score", "risk", "schema", "label"]
    
    for col in X.columns:
        for forbidden in forbidden_substrings:
            # We strictly prevent leakage
            assert forbidden not in col.lower()

def test_successful_baseline_training(synthetic_csv, tmp_path):
    model_out = str(tmp_path / "models" / "dev_baseline.joblib")
    
    metrics = train_and_save_baseline(synthetic_csv, model_out)
    
    assert os.path.exists(model_out)
    assert "accuracy" in metrics
    assert "f1_score" in metrics
    assert "confusion_matrix" in metrics
    assert isinstance(metrics["accuracy"], float)
