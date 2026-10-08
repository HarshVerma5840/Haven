# Haven Project Context

This document is a handoff brief for contributors joining the Haven project. It records the current repository state, the intended product, the target architecture, the finalized dataset contract, and the recommended implementation order.

## 1. Product summary

Haven is intended to be a privacy-first platform for proactive employee burnout detection and organizational insight. It uses aggregated behavioral metadata rather than message content or invasive surveillance. The long-term product direction includes:

- Burnout-risk detection from weekly employee/team signals.
- Privacy-preserving analytics with no raw personally identifiable information in the analytics store.
- Talent/network discovery using graph analysis.
- Team-level burnout contagion modeling using epidemiological methods such as SIR.
- AI-assisted HR insights and conversational analysis.

The current repository is an early-stage monorepo. The HRMS application is substantially present; the Haven analytics backend and ML pipeline are not yet implemented.

## 2. Repository layout and current state

```text
Haven/
├── README.md
├── PROJECT_CONTEXT.md             # This handoff document
├── haven-backend/                 # Planned Haven FastAPI backend; currently scaffold only
│   ├── .env.example
│   └── requirements.txt
└── hrms/                          # Frappe HRMS application and Docker setup
```

### Implemented today

- Frappe HRMS source, frontend, Docker setup, backup/restore scripts, and HR domain functionality exist under `hrms/`.
- A custom Frappe Employee field named `custom_github_username` exists in `hrms/hrms/add_custom_field.py`.
- Backend dependencies and environment placeholders are declared in `haven-backend/`.
- The backend dependency list already includes FastAPI, SQLAlchemy, Alembic, PostgreSQL support, Pandas, SciPy, NetworkX, Redis, Supabase, Google Gemini, and related libraries.

### Not implemented today

The following planned backend files and capabilities do not yet exist:

- FastAPI application and routes.
- SQLAlchemy models and Alembic migrations.
- Frappe API client.
- GitHub API client.
- Weekly aggregation task/scheduler.
- PostgreSQL metrics table.
- Dataset export pipeline.
- ML training, evaluation, and inference pipeline.
- Tests for the new backend and dataset pipeline.

Do not describe the backend as production-ready. It is currently a dependency/configuration scaffold.

## 3. Intended system architecture

```text
Frappe HRMS ───────┐
                   ├──> Haven data ingestion/aggregation backend ──> PostgreSQL analytics store
GitHub API ────────┘                                                │
                                                                    ├──> validated dataset export
                                                                    └──> ML training/inference
```

The architecture reference describes three main backend services:

1. `FrappeClient`: retrieves approved HR metrics and employee-to-GitHub mapping.
2. `GitHubClient`: retrieves approved engineering activity metrics for a defined reporting period.
3. `Aggregator`: joins the source metrics by pseudonymous employee identity and reporting week, validates the result, and persists one row per employee per week.

The aggregation job should be rerunnable and idempotent. The database must enforce:

```text
UNIQUE(employee_hash, week_start_date)
```

The reporting period must have an explicit timezone and definition. Prefer a calendar week with a documented timezone over an ambiguous “last seven days” window.

## 4. Privacy and security requirements

Privacy is a core product requirement, not a later enhancement.

- Do not store names, email addresses, raw GitHub usernames, raw HR identifiers, message content, or source API tokens in the analytics database.
- Generate `employee_hash` using a keyed, stable HMAC strategy. The secret key/salt must be stored outside the repository and must not change casually because changing it breaks longitudinal correlation.
- Keep any mapping between the hash and real identity in a separately protected identity vault, if the product requires re-identification.
- Use TLS, authenticated service-to-service requests, least-privilege credentials, and key rotation procedures.
- Encryption does not replace authorization. HRMS endpoints still need authentication and access controls.
- Do not expose employee-level risk results to unauthorized users. Apply role and scope checks to all API routes.
- Treat department, designation, employment type, grievance data, appraisal data, and payroll issue data as sensitive attributes.
- Add audit logging for data access and model-result access without logging raw secrets or PII.

The backend environment template already contains placeholders for `DATABASE_URL`, Supabase credentials, `VAULT_SALT`, `ENCRYPTION_KEY`, JWT settings, and the Gemini API key. Real values must never be committed.

## 5. Final dataset contract

The dataset grain is:

```text
one employee × one reporting week
```

Recommended primary business key:

```text
(employee_hash, week_start_date)
```

### Metadata and identifiers

| Column | Type | Role |
|---|---|---|
| `employee_hash` | string | Stable pseudonymous identifier; never a model feature |
| `week_start_date` | date | Reporting-period key; never a model feature |

### Model features

| Column | Type | Description |
|---|---|---|
| `department` | category | Employee department |
| `designation` | category | Employee designation |
| `employment_type` | category | Employment type |
| `tenure_months` | integer | Tenure in months |
| `team_size` | integer | Employees in the team during the reporting week |
| `avg_daily_work_hours` | float | Average daily working hours |
| `overtime_hours` | float | Weekly overtime hours |
| `late_entry_count` | integer | Late entries |
| `early_exit_count` | integer | Early exits |
| `missing_checkout_count` | integer | Missing checkout events |
| `weekend_work_days` | integer | Weekend workdays |
| `holiday_work_days` | integer | Holiday workdays |
| `consecutive_work_days` | integer | Longest consecutive work streak |
| `night_shift_count` | integer | Night shifts |
| `shift_change_count` | integer | Shift changes |
| `leave_days_taken` | integer | Leave days taken |
| `unused_leave_balance` | float | Unused leave balance |
| `unplanned_leave_count` | integer | Unplanned leave events |
| `leave_cancellation_count` | integer | Cancelled leave events |
| `timesheet_hours` | float | Weekly timesheet hours |
| `timesheet_correction_count` | integer | Timesheet corrections |
| `workload_change_percent` | float | Workload change from the prior week |
| `github_commit_count` | integer | GitHub commits |
| `after_hours_commit_count` | integer | Commits outside defined working hours |
| `weekend_commit_count` | integer | Weekend commits |
| `pull_request_count` | integer | Pull requests |
| `review_count` | integer | Code reviews |
| `review_response_hours` | float | Average review response time |
| `issue_count` | integer | GitHub issues created or assigned, as explicitly defined |
| `issue_resolution_hours` | float | Issue resolution time |
| `appraisal_rating` | float | Appraisal rating from 1 to 5 |
| `goal_completion_percent` | float | Goal completion percentage |
| `grievance_count` | integer | Grievances |
| `grievance_resolution_days` | float | Grievance resolution time |
| `travel_days` | integer | Business travel days |
| `payroll_issue_count` | integer | Payroll issues |

### Targets

| Column | Type | Role |
|---|---|---|
| `burnout_score` | float | Target in the range 0–1 |
| `burnout_risk` | category | Derived target: `Low`, `Medium`, or `High` |

Recommended target thresholds:

```text
0.00–0.33 → Low
0.34–0.66 → Medium
0.67–1.00 → High
```

`burnout_risk` must be derived from `burnout_score`; it is not an independent feature.

### Dataset quality/provenance columns

Add these columns to the stored dataset, even if they are not exposed to the model:

| Column | Type | Purpose |
|---|---|---|
| `schema_version` | string | Dataset contract version, e.g. `1.0` |
| `data_completeness` | float | Percentage of expected source data received |
| `source_timestamp` | timestamp | Extraction time |
| `label_source` | category | `synthetic`, `survey`, or `validated_hr_outcome` |

## 6. Data validation rules

- Count fields must be integers greater than or equal to zero.
- Hours and durations must be greater than or equal to zero.
- `appraisal_rating` must be between 1 and 5, or null when unavailable.
- Percentages must be between 0 and 100.
- `burnout_score` must be between 0 and 1.
- Categorical values must come from controlled vocabularies where possible.
- Missing values must remain distinguishable from true zero values.
- Every row must include `schema_version`, `data_completeness`, `source_timestamp`, and `label_source`.
- A row with missing source data must not silently convert missing values to zero.

## 7. Synthetic dataset policy

Because the HRMS endpoints and aggregator are not yet complete, create a synthetic dataset first so the ML and backend pipelines can be developed in parallel.

Recommended files:

```text
haven-backend/data/
├── synthetic_burnout_dataset.csv
├── burnout_dataset.csv
└── data_dictionary.csv
```

- `synthetic_burnout_dataset.csv` is for development and pipeline testing.
- `burnout_dataset.csv` is the production export generated from approved HRMS/GitHub data.
- `data_dictionary.csv` documents names, types, ranges, source systems, and missing-value rules.

The synthetic target formula must be documented and must not be presented as a clinically or scientifically validated burnout label. A model trained only on synthetic labels will learn the synthetic formula, not real burnout.

## 8. Parallel development workstreams

These tracks can proceed concurrently after the dataset contract is frozen.

### Track A: HRMS API

- Implement authenticated, narrowly scoped HRMS endpoints.
- Return approved weekly metrics rather than raw HR records.
- Support date/week filters and pagination if required.
- Define response schema and error behavior.
- Add tests for permissions, missing data, and date boundaries.
- Make the custom GitHub username field part of a proper migration/patch lifecycle.

### Track B: Haven backend

- Create FastAPI application structure.
- Add settings and secret loading.
- Implement SQLAlchemy models and Alembic migrations.
- Implement the Frappe and GitHub clients with timeouts, retries, pagination, and rate-limit handling.
- Implement aggregation, validation, HMAC hashing, and idempotent upsert.
- Add job execution and observability.
- Export the validated dataset.

### Track C: Machine learning

- Build a Pandas validation/preprocessing pipeline.
- Generate and inspect synthetic data.
- Establish a baseline model and evaluation protocol.
- Handle categorical values, missing values, class imbalance, and time-based splits.
- Add feature importance/explainability.
- Keep employee identity and reporting dates out of the feature matrix.
- Re-train and evaluate on real labels when they become available.

## 9. ML-specific risks

Potential leakage or sensitive proxies include:

- `appraisal_rating`
- `goal_completion_percent`
- `grievance_count`
- `grievance_resolution_days`
- `payroll_issue_count`

Maintain at least two experiment configurations:

1. An operational model using signals available before intervention or formal performance action.
2. A full model containing all approved features for comparison and research.

Use time-based validation rather than random row splitting when possible. The same employee appearing in both training and test data can produce overly optimistic results.

## 10. Recommended implementation order

1. Freeze this dataset contract and version it.
2. Create the data dictionary and synthetic dataset generator.
3. Create database models and migrations.
4. Build HRMS and GitHub client interfaces using mocks.
5. Build the aggregation and validation pipeline.
6. Build the baseline ML pipeline against synthetic data.
7. Implement authenticated HRMS endpoints.
8. Integrate real HRMS/GitHub data in a development environment.
9. Run end-to-end tests and data-quality checks.
10. Train and evaluate only after confirming label provenance and temporal correctness.

## 11. Definition of done for the first milestone

The first milestone is complete when:

- A versioned synthetic CSV can be generated reproducibly.
- Every row follows the schema and validation rules.
- A database migration creates the weekly metrics table.
- The aggregator can upsert a mocked weekly payload without duplicates.
- The ML pipeline can train and evaluate a baseline model.
- No raw PII or credentials appear in the generated analytics dataset.
- The HRMS API contract is documented and tested.

