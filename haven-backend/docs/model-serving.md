# Model Serving Layer

This document outlines the operational process for deploying and querying the burnout-risk model in the Haven backend.

## Placing the Kaggle Artifacts

The backend expects the model artifacts to be located exactly inside the `haven-backend/models/` directory. When exporting the pipeline from Kaggle, ensure the following three exact filenames are used:

1. `random_forest_pipeline.joblib`
   - The serialized Scikit-Learn `Pipeline` containing the imputation, preprocessing, and `RandomForestClassifier` steps.
2. `random_forest_metadata.json`
   - Metadata dictionary containing:
     - `"version"`: The model version.
     - `"model_type"`: e.g., `"Random Forest"`.
     - `"target"`: `"burnout_risk"`.
     - `"sklearn_version"`: Version of `scikit-learn` used during training. The backend requires `scikit-learn==1.6.1` to correctly deserialize the `.joblib` pipeline without version mismatch errors.
3. `feature_columns.json`
   - A JSON object detailing the exact feature names and strict order the model expects. Must contain `numeric_columns` and `categorical_columns` arrays.
   - Example:
     ```json
     {
       "numeric_columns": ["avg_daily_work_hours", "github_commit_count"],
       "categorical_columns": ["department"],
       "target": "burnout_risk",
       "identifier_column": "employee_hash",
       "excluded_columns": []
     }
     ```
   - *Note: A legacy plain-list format is also supported but not recommended.*

> **Note**: You can run `python validate_models.py` from the `haven-backend` directory to ensure your artifacts are structurally valid and safe to load!

> **Distribution Note**: These model artifacts (`.joblib`, `.json`) are typically distributed separately (e.g. via a secure storage bucket, Kaggle, or shared drive) because they are often ignored by Git to keep the repository lightweight and secure.

## Starting the Backend

Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

Run the FastAPI application:
```bash
uvicorn app.main:app --reload --port 8000
```
The model artifacts are lazily loaded into memory when the `ModelService` is first instantiated, or immediately on server boot if dependency injection initializes it.

### Readiness Check

You can verify that the API is up and that the model artifacts have loaded successfully by hitting the readiness endpoint:

**Request:**
`GET /ready`

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "database": "ok",
  "model": "ok"
}
```
If artifacts are missing or malformed, `"model"` will return `"unavailable"` and the overall `"status"` will be `"error"`.

## Calling the Prediction Endpoint

The model serving endpoint is available at `POST /api/v1/predictions`. It expects a `WeeklyEmployeeMetricsInput` payload inside a `"metrics"` key.
You can explicitly request a SHAP explanation for the prediction by setting `include_explanations: true`.

**Request (`POST`):**
```json
{
  "metrics": {
    "employee_hash": "anonymized123",
    "week_start_date": "2023-10-01",
    "department": "Engineering",
    "avg_daily_work_hours": 9.5,
    "github_commit_count": 25
  },
  "include_explanations": true
}
```

**Response (`200 OK`):**
```json
{
  "predicted_risk": "Medium",
  "probabilities": {
    "Low": 0.2,
    "Medium": 0.7,
    "High": 0.1
  },
  "model_type": "Random Forest",
  "model_version": "1.0",
  "schema_version": "1.0",
  "prediction_timestamp": "2023-10-02T10:00:00Z",
  "explanation": {
    "model_version": "rf-dev-1.1",
    "disclaimer": "SHAP values represent feature contributions to the model's prediction and are not causal explanations.",
    "explanations": {
      "High": {
        "top_positive": [
          {
            "feature": "avg_daily_work_hours",
            "contribution": 0.034,
            "direction": "positive",
            "description": "Avg Daily Work Hours increases the probability of High risk."
          }
        ],
        "top_negative": [
          {
            "feature": "department = Engineering",
            "contribution": -0.044,
            "direction": "negative",
            "description": "Department decreases the probability of High risk."
          }
        ]
      }
    }
  }
}
```

> **Security Note**: When `include_explanations` is requested, the prediction and its SHAP explanation will be saved to the Behavioral Vault. Identity variables are excluded from the SHAP calculations to preserve privacy.

## Redis Caching Layer

To improve performance and reduce redundant computations, prediction responses, SHAP explanations, and dashboard analytics are automatically cached in Redis. 

**Important:** Redis is used **strictly for non-persistent caching** of API responses to improve speed. It is **not** used for background workers, task queues (like Celery), or critical storage. 

### Local Redis Setup
To run Redis locally for development, you can use Docker:
```bash
docker run -p 6379:6379 -d redis:7
```

### Required Redis Variables
Configure Redis in your `.env` file using the following variables:
- `REDIS_URL`: Connection string (e.g., `redis://localhost:6379/0`).
- `CACHE_TTL_PREDICTION`: TTL in seconds for predictions and SHAP explanations (default: 3600).
- `CACHE_TTL_DASHBOARD`: TTL in seconds for employee/department dashboard summaries (default: 300).
- `CACHE_TTL_ANALYTICS`: TTL in seconds for NetworkX graphs and complex analytics (default: 86400).

### Cache Namespaces
Responses are strictly partitioned into distinct namespaces to prevent cache collisions and allow targeted invalidation:
- **Predictions**: `prediction:{employee_hash}:{week_start_date}:{model_version}:{input_data_hash}`
- **Explanations**: `explanation:prediction:{employee_hash}:{week_start_date}:{model_version}:{input_data_hash}`
- **Dashboards**: `analytics:dashboard:{department}:{start_date}:{end_date}:{filters_hash}:{model_version}`
- **NetworkX Graphs**: `analytics:graph:{graph_type}:{start_date}:{end_date}:{filters_hash}:{analysis_version}`

*Note: The `input_data_hash` and `filters_hash` are SHA-256 hashes of standardized JSON inputs, ensuring that minor variations in metric payloads perfectly bust the cache.*

### Privacy & Security
The caching layer (`CacheService`) automatically sanitizes payloads before storing them, ensuring that sensitive identity-vault fields (raw HRMS IDs, email addresses, GitHub usernames, tokens, and passwords) are **never** persisted to Redis.

### Health-Check & Graceful Fallback
The `CacheService` includes an `is_available()` health check. If Redis is down, unreachable, or experiences a sudden connection timeout, the API will seamlessly fall back to recomputing the data (via the database or ML model) and return it to the client normally. It avoids HTTP 500 errors and ensures zero downtime during cache outages.

## Model Versioning

Model versioning is handled declaratively via the `random_forest_metadata.json` file. The `"version"` attribute from this file is propagated directly into the `PredictionResponse` so consumers always know exactly which model generated the probability distribution. Backwards compatibility should be managed by keeping legacy models hosted under distinct paths, or appending the version to the API path if major schema changes occur.

## Why the Current Model is Development-Only

The current prediction pipeline and models trained off synthetic Kaggle datasets are **development-only**. They should **never** be used to inform real HR interventions because:
1. They are trained on artificially generated targets based on mathematical formulas, not clinical burnout realities.
2. They do not account for unique organizational dynamics present in your actual company.
3. Deploying synthetic models on real employees creates a dangerous feedback loop where real-world safety decisions are made by synthetic proxy logic.
