import pytest
import datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.database.models import WeeklyEmployeeMetrics
from app.services.aggregation_service import AggregationService
from app.schemas.github import GitHubWeeklyMetrics
from app.services.github_metrics import GitHubMetricsExtractor

@pytest.fixture
def mock_github_extractor():
    extractor = AsyncMock(spec=GitHubMetricsExtractor)
    extractor.extract_weekly_metrics.return_value = GitHubWeeklyMetrics(
        github_username="testuser",
        week_start_date=datetime.date(2026, 10, 5),
        github_commit_count=10,
        after_hours_commit_count=2,
        weekend_commit_count=1,
        pull_request_count=3,
        review_count=5,
        review_response_hours=1.5,
        issue_count=2,
        issue_resolution_hours=24.0
    )
    return extractor

@pytest.fixture
def aggregation_service(db_session, mock_github_extractor):
    return AggregationService(db=db_session, github_extractor=mock_github_extractor)

@pytest.mark.anyio
async def test_first_insert(aggregation_service, db_session):
    record = await aggregation_service.aggregate_github_metrics(
        employee_hash="hash123",
        github_username="testuser",
        week_start_date=datetime.date(2026, 10, 5),
        week_end_date=datetime.date(2026, 10, 11)
    )
    
    assert record.id is not None
    assert record.employee_hash == "hash123"
    assert record.github_commit_count == 10
    assert record.schema_version == "1.0"
    assert record.label_source == "pending"
    assert record.source_timestamp is not None
    assert record.data_completeness == 0.5
    
    # Verify no GitHub username is stored
    assert not hasattr(record, "github_username")
    
    # Verify HRMS fields are NULL
    assert record.department is None
    assert record.designation is None

@pytest.mark.anyio
async def test_existing_employee_week_update(aggregation_service, db_session, mock_github_extractor):
    # First insert
    record1 = await aggregation_service.aggregate_github_metrics(
        employee_hash="hash123",
        github_username="testuser",
        week_start_date=datetime.date(2026, 10, 5),
        week_end_date=datetime.date(2026, 10, 11)
    )
    
    # Change mock for update
    mock_github_extractor.extract_weekly_metrics.return_value.github_commit_count = 20
    
    # Second update
    record2 = await aggregation_service.aggregate_github_metrics(
        employee_hash="hash123",
        github_username="testuser",
        week_start_date=datetime.date(2026, 10, 5),
        week_end_date=datetime.date(2026, 10, 11)
    )
    
    assert record1.id == record2.id
    assert record2.github_commit_count == 20
    
    # Verify duplicate prevention
    count = db_session.query(WeeklyEmployeeMetrics).count()
    assert count == 1

@pytest.mark.anyio
async def test_multiple_employees(aggregation_service, db_session):
    await aggregation_service.aggregate_github_metrics(
        employee_hash="hash123",
        github_username="testuser1",
        week_start_date=datetime.date(2026, 10, 5),
        week_end_date=datetime.date(2026, 10, 11)
    )
    
    await aggregation_service.aggregate_github_metrics(
        employee_hash="hash456",
        github_username="testuser2",
        week_start_date=datetime.date(2026, 10, 5),
        week_end_date=datetime.date(2026, 10, 11)
    )
    
    count = db_session.query(WeeklyEmployeeMetrics).count()
    assert count == 2

@pytest.mark.anyio
async def test_github_extraction_failure(aggregation_service, db_session, mock_github_extractor):
    mock_github_extractor.extract_weekly_metrics.side_effect = Exception("API down")
    from app.services.aggregation_service import AggregationError
    
    with pytest.raises(AggregationError, match="API down"):
        await aggregation_service.aggregate_github_metrics(
            employee_hash="hash123",
            github_username="testuser",
            week_start_date=datetime.date(2026, 10, 5),
            week_end_date=datetime.date(2026, 10, 11)
        )
        
    count = db_session.query(WeeklyEmployeeMetrics).count()
    assert count == 0

@pytest.mark.anyio
async def test_database_rollback_on_mapping_error(aggregation_service, db_session, mock_github_extractor, monkeypatch):
    # Monkeypatch session.commit to fail
    def mock_commit():
        raise Exception("DB constraint failed")
    
    monkeypatch.setattr(db_session, "commit", mock_commit)
    
    with pytest.raises(Exception, match="DB constraint failed"):
        await aggregation_service.aggregate_github_metrics(
            employee_hash="hash123",
            github_username="testuser",
            week_start_date=datetime.date(2026, 10, 5),
            week_end_date=datetime.date(2026, 10, 11)
        )


@pytest.mark.anyio
async def test_input_validation(aggregation_service):
    with pytest.raises(ValueError, match="employee_hash and github_username are required"):
        await aggregation_service.aggregate_github_metrics(
            employee_hash="",
            github_username="testuser",
            week_start_date=datetime.date(2026, 10, 5),
            week_end_date=datetime.date(2026, 10, 11)
        )


@pytest.mark.anyio
async def test_preservation_of_hrms_and_target_values(aggregation_service, db_session, mock_github_extractor):
    # Setup initial record with HRMS and target values
    start_date = datetime.date(2026, 10, 5)
    initial_record = WeeklyEmployeeMetrics(
        employee_hash="hash_preserve",
        week_start_date=start_date,
        department="Engineering",
        designation="Senior Engineer",
        burnout_score=0.75,
        burnout_risk="High",
        label_source="manual",
        schema_version="1.0"
    )
    db_session.add(initial_record)
    db_session.commit()

    # Act
    record = await aggregation_service.aggregate_github_metrics(
        employee_hash="hash_preserve",
        github_username="testuser",
        week_start_date=start_date,
        week_end_date=datetime.date(2026, 10, 11)
    )

    # Assert HRMS values preserved
    assert record.department == "Engineering"
    assert record.designation == "Senior Engineer"
    
    # Assert burnout/target values preserved
    assert record.burnout_score == 0.75
    assert record.burnout_risk == "High"
    assert record.label_source == "manual"
    
    # Assert GitHub metrics applied
    assert record.github_commit_count == 10
