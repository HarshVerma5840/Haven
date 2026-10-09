import pytest
from pydantic import ValidationError
from datetime import date
from app.schemas.github import GitHubWeeklyMetrics

def test_github_weekly_metrics_valid():
    data = {
        "github_username": "octocat",
        "week_start_date": "2026-10-05",
        "github_commit_count": 10,
        "after_hours_commit_count": 2,
        "weekend_commit_count": 0,
        "pull_request_count": 3,
        "review_count": 5,
        "review_response_hours": 1.5,
        "issue_count": 2,
        "issue_resolution_hours": 24.0,
    }
    metrics = GitHubWeeklyMetrics(**data)
    assert metrics.github_username == "octocat"
    assert metrics.week_start_date == date(2026, 10, 5)
    assert metrics.github_commit_count == 10
    assert metrics.review_response_hours == 1.5

def test_github_weekly_metrics_optional_fields():
    data = {
        "github_username": "octocat",
        "week_start_date": "2026-10-05",
    }
    metrics = GitHubWeeklyMetrics(**data)
    # Default values should be correctly applied
    assert metrics.github_commit_count == 0
    assert metrics.review_response_hours is None
    assert metrics.issue_resolution_hours is None

def test_github_weekly_metrics_negative_counts():
    data = {
        "github_username": "octocat",
        "week_start_date": "2026-10-05",
        "github_commit_count": -1,
    }
    with pytest.raises(ValidationError) as exc_info:
        GitHubWeeklyMetrics(**data)
    
    errors = exc_info.value.errors()
    assert any("greater than or equal to 0" in e["msg"] for e in errors) or any("ge" in e["type"] for e in errors)

def test_github_weekly_metrics_negative_durations():
    data = {
        "github_username": "octocat",
        "week_start_date": "2026-10-05",
        "review_response_hours": -5.0,
    }
    with pytest.raises(ValidationError) as exc_info:
        GitHubWeeklyMetrics(**data)
        
    errors = exc_info.value.errors()
    assert any("greater than or equal to 0" in e["msg"] for e in errors) or any("ge" in e["type"] for e in errors)

def test_github_weekly_metrics_invalid_date():
    data = {
        "github_username": "octocat",
        "week_start_date": "not-a-date",
    }
    with pytest.raises(ValidationError):
        GitHubWeeklyMetrics(**data)

def test_github_weekly_metrics_empty_username():
    data = {
        "github_username": "",
        "week_start_date": "2026-10-05",
    }
    with pytest.raises(ValidationError) as exc_info:
        GitHubWeeklyMetrics(**data)
    errors = exc_info.value.errors()
    assert any(e["type"] == "string_too_short" for e in errors)
