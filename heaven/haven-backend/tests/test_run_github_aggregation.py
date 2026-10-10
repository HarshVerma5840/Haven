import pytest
import datetime
import sys
from unittest.mock import AsyncMock, patch, MagicMock

from app.tasks.run_github_aggregation import run_aggregation, main
from app.schemas.github import GitHubWeeklyMetrics
from app.services.aggregation_service import AggregationError

@pytest.fixture
def mock_client_cls():
    with patch("app.tasks.run_github_aggregation.GitHubClient") as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value = client_instance
        yield MockClient, client_instance

@pytest.fixture
def mock_extractor_cls():
    with patch("app.tasks.run_github_aggregation.GitHubMetricsExtractor") as MockExtractor:
        extractor_instance = AsyncMock()
        extractor_instance.extract_weekly_metrics.return_value = GitHubWeeklyMetrics(
            github_username="testuser",
            week_start_date=datetime.date(2026, 10, 5),
            github_commit_count=5,
            after_hours_commit_count=1,
            weekend_commit_count=0,
            pull_request_count=0,
            review_count=0,
            review_response_hours=None,
            issue_count=0,
            issue_resolution_hours=None
        )
        MockExtractor.return_value = extractor_instance
        yield MockExtractor, extractor_instance

@pytest.fixture
def mock_session_local(db_session):
    with patch("app.tasks.run_github_aggregation.SessionLocal") as MockSessionLocal, \
         patch("app.tasks.run_github_aggregation.BehavioralSessionLocal") as MockBehavSessionLocal:
        # Instead of closing the actual session (which the fixture manages), we'll wrap it
        mock_db = MagicMock(wraps=db_session.behav)
        MockSessionLocal.return_value = mock_db
        MockBehavSessionLocal.return_value = mock_db
        yield mock_db

@pytest.mark.anyio
async def test_successful_aggregation(mock_client_cls, mock_extractor_cls, mock_session_local):
    _, mock_client = mock_client_cls
    
    with patch("app.tasks.run_github_aggregation.logger") as mock_logger:
        record = await run_aggregation(
            employee_hash="hash_success",
            github_username="testuser",
            week_start_date=datetime.date(2026, 10, 5),
            week_end=datetime.date(2026, 10, 11)
        )
        
        assert record.github_commit_count == 5
        assert record.employee_hash == "hash_success"
        
        # Verify client and session cleanup
        mock_client.close.assert_awaited_once()
        mock_session_local.close.assert_called_once()
        
        # Verify safe logging
        mock_logger.info.assert_any_call(
            "Aggregation completed successfully",
            employee_hash="hash_success",
            record_id=record.id,
            commits=5,
            prs=0,
            issues=0
        )
        
        # Ensure raw github username is not in info logging kwargs
        for call in mock_logger.info.call_args_list:
            kwargs = call.kwargs
            assert "github_username" not in kwargs

@pytest.mark.anyio
async def test_github_api_failure(mock_client_cls, mock_extractor_cls, mock_session_local):
    _, mock_client = mock_client_cls
    _, mock_extractor = mock_extractor_cls
    
    mock_extractor.extract_weekly_metrics.side_effect = Exception("GH API down")
    
    with patch("app.tasks.run_github_aggregation.logger") as mock_logger:
        with pytest.raises(AggregationError):
            await run_aggregation(
                employee_hash="hash_fail",
                github_username="testuser",
                week_start_date=datetime.date(2026, 10, 5),
                week_end=datetime.date(2026, 10, 11)
            )
            
        mock_logger.error.assert_called_with("Aggregation failed due to GitHub API error", error="GitHub extraction failed: GH API down")
        
        # Verify cleanup happens even on error
        mock_client.close.assert_awaited_once()
        mock_session_local.close.assert_called_once()

@pytest.mark.anyio
async def test_database_failure(mock_client_cls, mock_extractor_cls, mock_session_local):
    _, mock_client = mock_client_cls
    
    mock_session_local.commit.side_effect = Exception("DB Lock Error")
    
    with patch("app.tasks.run_github_aggregation.logger") as mock_logger:
        with pytest.raises(Exception, match="DB Lock Error"):
            await run_aggregation(
                employee_hash="hash_db_fail",
                github_username="testuser",
                week_start_date=datetime.date(2026, 10, 5),
                week_end=datetime.date(2026, 10, 11)
            )
            
        mock_logger.error.assert_called_with("Aggregation failed due to internal error", error="DB Lock Error")
        
        # Verify cleanup happens even on error
        mock_client.close.assert_awaited_once()
        mock_session_local.close.assert_called_once()

def test_main_cli_success(mock_client_cls, mock_extractor_cls, mock_session_local, monkeypatch):
    test_args = [
        "run_github_aggregation",
        "--employee-hash", "hash_cli",
        "--github-username", "cli_user",
        "--week-start", "2026-10-05",
        "--week-end", "2026-10-11"
    ]
    monkeypatch.setattr(sys, "argv", test_args)
    
    # main() is synchronous and calls asyncio.run internally
    main()
    
    # If it didn't exit(1), it was successful
    mock_session_local.close.assert_called_once()

from app.tasks.run_github_aggregation import run_all_employees_aggregation
from app.database.models import IdentityMapping, WeeklyEmployeeMetrics
from app.security.encryption import encrypt_value

@pytest.mark.anyio
async def test_batch_aggregation_with_employee_mapping(mock_client_cls, mock_extractor_cls, db_session):
    _, mock_client = mock_client_cls
    iden_sess = db_session.iden
    behav_sess = db_session.behav

    iden_sess.query(IdentityMapping).delete()
    iden_sess.add(IdentityMapping(
        employee_hash="emp_hash_mapped",
        github_username=encrypt_value("octocat_dev"),
        hrms_employee_id=encrypt_value("HR-001")
    ))
    iden_sess.add(IdentityMapping(
        employee_hash="emp_hash_no_gh",
        github_username=None, # Missing username should skip gracefully without crash
        hrms_employee_id=encrypt_value("HR-002")
    ))
    iden_sess.flush()

    result = await run_all_employees_aggregation(
        week_start_date=datetime.date(2026, 10, 5),
        week_end=datetime.date(2026, 10, 11),
        identity_db=iden_sess,
        behavioral_db=behav_sess,
        client=mock_client
    )

    assert result["status"] == "completed"
    assert result["total_mapped_employees"] == 2
    assert result["processed"] == 1
    assert result["skipped_no_github_username"] == 1
    assert result["failed"] == 0

@pytest.mark.anyio
async def test_anonymized_storage_and_no_secret_leakage(mock_client_cls, mock_extractor_cls, db_session, monkeypatch):
    test_secret_token = "ghp_SuperSecretToken1234567890ABCDEF"
    monkeypatch.setenv("GITHUB_TOKEN", test_secret_token)
    
    _, mock_client = mock_client_cls
    iden_sess = db_session.iden
    behav_sess = db_session.behav

    iden_sess.query(IdentityMapping).delete()
    iden_sess.add(IdentityMapping(
        employee_hash="emp_hash_anon",
        github_username=encrypt_value("developer_user"),
        hrms_employee_id=encrypt_value("HR-999")
    ))
    iden_sess.flush()

    captured_logs = []
    with patch("app.tasks.run_github_aggregation.logger") as mock_logger:
        def log_info(msg, **kwargs):
            captured_logs.append((msg, kwargs))
        def log_warning(msg, **kwargs):
            captured_logs.append((msg, kwargs))
        def log_error(msg, **kwargs):
            captured_logs.append((msg, kwargs))
            
        mock_logger.info.side_effect = log_info
        mock_logger.warning.side_effect = log_warning
        mock_logger.error.side_effect = log_error

        result = await run_all_employees_aggregation(
            week_start_date=datetime.date(2026, 10, 5),
            week_end=datetime.date(2026, 10, 11),
            identity_db=iden_sess,
            behavioral_db=behav_sess,
            client=mock_client
        )

        assert result["processed"] == 1

        # 1. Verify anonymized storage in Behavioral Vault
        record = behav_sess.query(WeeklyEmployeeMetrics).filter_by(employee_hash="emp_hash_anon").first()
        assert record is not None
        assert record.employee_hash == "emp_hash_anon"
        # Confirm WeeklyEmployeeMetrics table has NO column for github_username or any raw identity
        assert not hasattr(record, "github_username")
        assert not hasattr(record, "custom_github_username")
        assert not hasattr(record, "hrms_employee_id")
        # Confirm aggregate metrics are stored
        assert record.github_commit_count == 5
        assert record.after_hours_commit_count == 1
        assert record.weekend_commit_count == 0

        # 2. Verify no secret token or raw username leakage in logs
        for msg, kwargs in captured_logs:
            full_log_str = str(msg) + str(kwargs)
            assert test_secret_token not in full_log_str
            assert "developer_user" not in full_log_str
            assert "github_username" not in kwargs

@pytest.mark.anyio
async def test_batch_aggregation_handles_employee_failure(mock_client_cls, mock_extractor_cls, db_session):
    _, mock_client = mock_client_cls
    _, mock_extractor = mock_extractor_cls
    iden_sess = db_session.iden
    behav_sess = db_session.behav

    iden_sess.query(IdentityMapping).delete()
    iden_sess.add(IdentityMapping(
        employee_hash="emp_hash_fail",
        github_username=encrypt_value("failing_user"),
        hrms_employee_id=encrypt_value("HR-003")
    ))
    iden_sess.flush()

    mock_extractor.extract_weekly_metrics.side_effect = Exception("Repository access failed")

    result = await run_all_employees_aggregation(
        week_start_date=datetime.date(2026, 10, 5),
        week_end=datetime.date(2026, 10, 11),
        identity_db=iden_sess,
        behavioral_db=behav_sess,
        client=mock_client
    )

    assert result["status"] == "completed"
    assert result["total_mapped_employees"] == 1
    assert result["processed"] == 0
    assert result["failed"] == 1

