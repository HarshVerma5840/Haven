"""Train the Haven Random Forest burnout-risk baseline.

This script is for development only. It trains on the supplied dataset and
stores preprocessing and the classifier together in one joblib pipeline.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


NUMERIC_COLUMNS = [
    "tenure_months",
    "team_size",
    "avg_daily_work_hours",
    "overtime_hours",
    "late_entry_count",
    "early_exit_count",
    "missing_checkout_count",
    "weekend_work_days",
    "holiday_work_days",
    "consecutive_work_days",
    "night_shift_count",
    "shift_change_count",
    "leave_days_taken",
    "unused_leave_balance",
    "unplanned_leave_count",
    "leave_cancellation_count",
    "timesheet_hours",
    "timesheet_correction_count",
    "workload_change_percent",
    "github_commit_count",
    "after_hours_commit_count",
    "weekend_commit_count",
    "pull_request_count",
    "review_count",
    "review_response_hours",
    "issue_count",
    "issue_resolution_hours",
    "appraisal_rating",
    "goal_completion_percent",
    "grievance_count",
    "grievance_resolution_days",
    "travel_days",
    "payroll_issue_count",
]

CATEGORICAL_COLUMNS = ["department", "designation", "employment_type"]
TARGET_COLUMN = "burnout_risk"
IDENTIFIER_COLUMN = "employee_hash"
DATE_COLUMN = "week_start_date"
LABELS = ["Low", "Medium", "High"]


def build_pipeline() -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_COLUMNS),
            ("categorical", categorical_pipeline, CATEGORICAL_COLUMNS),
        ],
        remainder="drop",
    )

    classifier = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def train_random_forest(
    csv_path: str | Path,
    model_path: str | Path,
    metadata_path: str | Path,
    features_path: str | Path,
    test_size: float = 0.2,
) -> dict:
    csv_path = Path(csv_path)
    model_path = Path(model_path)
    metadata_path = Path(metadata_path)
    features_path = Path(features_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_columns = {
        IDENTIFIER_COLUMN,
        DATE_COLUMN,
        TARGET_COLUMN,
        *NUMERIC_COLUMNS,
        *CATEGORICAL_COLUMNS,
    }
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    df = df.dropna(subset=[TARGET_COLUMN]).copy()
    if set(df[TARGET_COLUMN].unique()) != set(LABELS):
        raise ValueError(f"The target must contain all three risk classes: {LABELS}")

    X = df[NUMERIC_COLUMNS + CATEGORICAL_COLUMNS]
    y = df[TARGET_COLUMN].astype(str)
    groups = df[IDENTIFIER_COLUMN].astype(str)

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    train_indices, test_indices = next(splitter.split(X, y, groups=groups))

    pipeline = build_pipeline()
    pipeline.fit(X.iloc[train_indices], y.iloc[train_indices])

    predictions = pipeline.predict(X.iloc[test_indices])
    report = classification_report(
        y.iloc[test_indices],
        predictions,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y.iloc[test_indices], predictions, labels=LABELS)

    metrics = {
        "accuracy": float(accuracy_score(y.iloc[test_indices], predictions)),
        "macro_precision": float(
            precision_score(y.iloc[test_indices], predictions, average="macro", zero_division=0)
        ),
        "macro_recall": float(
            recall_score(y.iloc[test_indices], predictions, average="macro", zero_division=0)
        ),
        "macro_f1": float(
            f1_score(y.iloc[test_indices], predictions, average="macro", zero_division=0)
        ),
        "high_risk_precision": float(report.get("High", {}).get("precision", 0.0)),
        "high_risk_recall": float(report.get("High", {}).get("recall", 0.0)),
        "high_risk_f1": float(report.get("High", {}).get("f1-score", 0.0)),
        "classification_report": report,
        "confusion_matrix_labels": LABELS,
        "confusion_matrix": matrix.tolist(),
        "train_rows": int(len(train_indices)),
        "test_rows": int(len(test_indices)),
        "train_employees": int(groups.iloc[train_indices].nunique()),
        "test_employees": int(groups.iloc[test_indices].nunique()),
        "class_distribution": y.value_counts().to_dict(),
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    features_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)

    metadata = {
        "model_type": "RandomForestClassifier",
        "model_version": "rf-1.0",
        "target": TARGET_COLUMN,
        "schema_version": "1.0",
        "sklearn_version": sklearn.__version__,
        "feature_columns": {
            "numeric_columns": NUMERIC_COLUMNS,
            "categorical_columns": CATEGORICAL_COLUMNS,
            "excluded_columns": [IDENTIFIER_COLUMN, DATE_COLUMN]
        },
        "identifier_column": IDENTIFIER_COLUMN,
        "date_column": DATE_COLUMN,
        "training_dataset": str(csv_path),
        "label_source": sorted(df["label_source"].dropna().unique().tolist())
        if "label_source" in df.columns
        else None,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    features_json = {
        "numeric_columns": NUMERIC_COLUMNS,
        "categorical_columns": CATEGORICAL_COLUMNS,
        "target": TARGET_COLUMN,
        "identifier_column": IDENTIFIER_COLUMN,
        "excluded_columns": [DATE_COLUMN]
    }
    features_path.write_text(json.dumps(features_json, indent=2), encoding="utf-8")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default="data/synthetic_burnout_dataset.csv",
        help="Path to the training CSV",
    )
    parser.add_argument(
        "--model-output",
        default="models/random_forest_pipeline.joblib",
        help="Output path for the pipeline artifact",
    )
    parser.add_argument(
        "--metadata-output",
        default="models/random_forest_metadata.json",
        help="Output path for training metadata",
    )
    parser.add_argument(
        "--features-output",
        default="models/feature_columns.json",
        help="Output path for feature columns JSON",
    )
    args = parser.parse_args()

    metrics = train_random_forest(
        csv_path=args.csv,
        model_path=args.model_output,
        metadata_path=args.metadata_output,
        features_path=args.features_output,
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
