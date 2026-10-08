import pytest
from sqlalchemy.exc import IntegrityError
from datetime import date
from app.database.models import WeeklyEmployeeMetrics

def test_weekly_employee_metrics_constraints(db_session):
    # Test valid model
    metric1 = WeeklyEmployeeMetrics(
        employee_hash="hash1",
        week_start_date=date(2026, 1, 1),
        schema_version="1.0",
        label_source="synthetic",
        burnout_score=0.5,
        appraisal_rating=3.0,
        team_size=5
    )
    db_session.add(metric1)
    db_session.commit()
    
    # Test unique constraint (same hash and date)
    metric2 = WeeklyEmployeeMetrics(
        employee_hash="hash1",
        week_start_date=date(2026, 1, 1),
        schema_version="1.0",
        label_source="synthetic",
        burnout_score=0.2,
        appraisal_rating=4.0
    )
    db_session.add(metric2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Test valid second model (different date)
    metric3 = WeeklyEmployeeMetrics(
        employee_hash="hash1",
        week_start_date=date(2026, 1, 8),
        schema_version="1.0",
        label_source="synthetic",
        burnout_score=0.2,
        appraisal_rating=4.0
    )
    db_session.add(metric3)
    db_session.commit()
    assert metric3.id is not None
