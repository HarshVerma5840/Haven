import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from ml.data_loader import load_and_preprocess_data
from ml.evaluate import evaluate_classification_model

import structlog

logger = structlog.get_logger(__name__)

def train_and_save_baseline(csv_path: str, model_output_path: str):
    """
    Trains a baseline model on the synthetic dataset.
    This model is solely for structural pipeline validation and is strictly trained
    on non-real SYNTHETIC data. It holds NO clinical or scientific validity.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    logger.info("Loading synthetic dataset", path=csv_path)
    X, y = load_and_preprocess_data(csv_path)
    
    # Simple randomized split. If the dataset had timestamps easily parseable as index,
    # a TimeSeriesSplit would be used.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    logger.info("Training baseline RandomForest model on synthetic data...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    logger.info("Evaluating model predictions")
    y_pred = clf.predict(X_test)
    metrics = evaluate_classification_model(y_test, y_pred, labels=["Low", "Medium", "High"])
    
    # Save the model
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(clf, model_output_path)
    logger.info("Saved SYNTHETIC baseline model locally", model_path=model_output_path)
    
    return metrics

if __name__ == "__main__":
    train_and_save_baseline(
        csv_path="data/synthetic_burnout_dataset.csv",
        model_output_path="models/dev_baseline_synthetic.joblib"
    )
