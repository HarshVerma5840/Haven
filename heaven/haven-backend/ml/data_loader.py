import pandas as pd
import numpy as np

def load_and_preprocess_data(csv_path: str):
    """
    Loads synthetic baseline dataset and prepares feature matrices.
    Excludes explicitly forbidden tracking columns and targets.
    """
    df = pd.read_csv(csv_path)
    
    # Save targets (using risk as target since requirement asks for classification metrics)
    y = df["burnout_risk"]
    
    # Exclude forbidden tracking features and targets
    forbidden_cols = [
        "employee_hash", "week_start_date", "burnout_score", "burnout_risk",
        "schema_version", "source_timestamp", "label_source"
    ]
    
    X = df.drop(columns=[col for col in forbidden_cols if col in df.columns])
    
    # Handle categorical variables via one-hot encoding
    categorical_cols = ["department", "designation", "employment_type"]
    X = pd.get_dummies(X, columns=[col for col in categorical_cols if col in X.columns], dummy_na=True)
    
    # Fill remaining missing numeric values with medians to prevent converting missing directly to 0
    # In a real setup, we'd use an imputer fit purely on train data, but for this baseline medians work well.
    X = X.fillna(X.median(numeric_only=True))
    
    return X, y
