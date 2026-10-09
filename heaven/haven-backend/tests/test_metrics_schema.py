import pytest
from datetime import date, datetime
from pydantic import ValidationError
from app.schemas.metrics import WeeklyEmployeeMetricsInput

def test_valid_record():
    record = WeeklyEmployeeMetricsInput(
        employee_hash="hash123",
        week_start_date=date(2026, 10, 5),
        department="Engineering",
        tenure_months=12.5,
        github_commit_count=10,
        burnout_score=0.4,
        burnout_risk="Medium",
        goal_completion_percent=85.0
    )
    assert record.employee_hash == "hash123"
    assert record.department == "Engineering"
    assert record.github_commit_count == 10
    assert record.burnout_risk == "Medium"
    assert record.schema_version == "1.0"

def test_missing_optional_fields():
    # Only required fields are employee_hash and week_start_date
    record = WeeklyEmployeeMetricsInput(
        employee_hash="hash123",
        week_start_date=date(2026, 10, 5)
    )
    assert record.employee_hash == "hash123"
    assert record.department is None
    assert record.github_commit_count is None
    assert record.label_source == "pending"

def test_invalid_ranges_negative_counts():
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            github_commit_count=-5
        )
    assert "github_commit_count" in str(excinfo.value)

def test_invalid_ranges_negative_durations():
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            review_response_hours=-1.5
        )
    assert "review_response_hours" in str(excinfo.value)

def test_invalid_ranges_percentages():
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            goal_completion_percent=105.0
        )
    assert "goal_completion_percent" in str(excinfo.value)
    
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            workload_change_percent=-10.0
        )
    assert "workload_change_percent" in str(excinfo.value)

def test_invalid_appraisal_rating():
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            appraisal_rating=0.5
        )
    assert "appraisal_rating" in str(excinfo.value)
    
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            appraisal_rating=5.5
        )
    assert "appraisal_rating" in str(excinfo.value)

def test_invalid_burnout_score():
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            burnout_score=1.1
        )
    assert "burnout_score" in str(excinfo.value)
    
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            burnout_score=-0.1
        )
    assert "burnout_score" in str(excinfo.value)

def test_invalid_burnout_risk():
    with pytest.raises(ValidationError) as excinfo:
        WeeklyEmployeeMetricsInput(
            employee_hash="hash123",
            week_start_date=date(2026, 10, 5),
            burnout_risk="Critical"
        )
    assert "burnout_risk" in str(excinfo.value)
