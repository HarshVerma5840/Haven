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
    with patch("app.tasks.run_github_aggregation.BehavioralSessionLocal") as MockSessionLocal:
        # Instead of closing the actual session (which the fixture manages), we'll wrap it
        mock_db = MagicMock(wraps=db_session.behav)
        MockSessionLocal.return_value = mock_db
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
