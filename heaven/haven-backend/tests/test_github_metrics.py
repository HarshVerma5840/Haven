import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.services.github_metrics import GitHubMetricsExtractor
from app.services.github_client import GitHubClient
from app.config import get_settings

@pytest.fixture
def mock_client():
    client = GitHubClient()
    client.get_paginated = AsyncMock()
    return client

@pytest.fixture
def extractor(mock_client):
    settings = get_settings()
    settings.github_repositories = ["org/repo1"]
    return GitHubMetricsExtractor(mock_client)

@pytest.mark.anyio
async def test_no_activity(extractor, mock_client):
    mock_client.get_paginated.return_value = []
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    
    assert metrics.github_commit_count == 0
    assert metrics.after_hours_commit_count == 0
    assert metrics.weekend_commit_count == 0
    assert metrics.pull_request_count == 0
    assert metrics.review_count == 0
    assert metrics.review_response_hours is None
    assert metrics.issue_count == 0
    assert metrics.issue_resolution_hours is None

@pytest.mark.anyio
async def test_events_working_hours(extractor, mock_client):
    # Monday 2026-10-05 10:00:00 UTC (within 09:00 - 17:00 UTC default)
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo1/commits": [
            {"sha": "123", "commit": {"author": {"date": "2026-10-05T10:00:00Z"}}}
        ],
        "repos/org/repo1/issues": [
            {
                "id": 1,
                "created_at": "2026-10-05T10:00:00Z",
                "closed_at": "2026-10-05T12:00:00Z", # 2 hours resolution
                "user": {"login": "testuser"}
            }
        ],
    }.get(path, [])
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    
    assert metrics.github_commit_count == 1
    assert metrics.after_hours_commit_count == 0
    assert metrics.weekend_commit_count == 0
    assert metrics.issue_count == 1
    assert metrics.issue_resolution_hours == 2.0

@pytest.mark.anyio
async def test_events_outside_working_hours(extractor, mock_client):
    # Monday 2026-10-05 08:00:00 UTC (before 09:00)
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo1/commits": [
            {"sha": "123", "commit": {"author": {"date": "2026-10-05T08:00:00Z"}}},
            {"sha": "456", "commit": {"author": {"date": "2026-10-05T18:00:00Z"}}} # after 17:00
        ],
        "repos/org/repo1/issues": []
    }.get(path, [])
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 2
    assert metrics.after_hours_commit_count == 2
    assert metrics.weekend_commit_count == 0

@pytest.mark.anyio
async def test_weekend_events(extractor, mock_client):
    # Saturday 2026-10-10 12:00:00 UTC
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo1/commits": [
            {"sha": "123", "commit": {"author": {"date": "2026-10-10T12:00:00Z"}}}
        ],
        "repos/org/repo1/issues": []
    }.get(path, [])
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 1
    assert metrics.weekend_commit_count == 1

@pytest.mark.anyio
async def test_duplicate_events_and_multiple_repos(extractor, mock_client):
    extractor.repos = ["org/repo1", "org/repo2"]
    
    def side_effect(path, params=None):
        if path == "repos/org/repo1/commits":
            return [{"sha": "dup_sha", "commit": {"author": {"date": "2026-10-05T10:00:00Z"}}}]
        elif path == "repos/org/repo2/commits":
            return [{"sha": "dup_sha", "commit": {"author": {"date": "2026-10-05T10:00:00Z"}}}]
        elif path == "repos/org/repo1/issues":
            return [{"id": 99, "created_at": "2026-10-05T10:00:00Z", "user": {"login": "testuser"}}]
        elif path == "repos/org/repo2/issues":
            return [{"id": 99, "created_at": "2026-10-05T10:00:00Z", "user": {"login": "testuser"}}]
        return []

    mock_client.get_paginated.side_effect = side_effect
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 1
    assert metrics.issue_count == 1

@pytest.mark.anyio
async def test_missing_timestamps(extractor, mock_client):
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo1/commits": [
            {"sha": "123", "commit": {"author": {"date": None}}}
        ],
        "repos/org/repo1/issues": [
            {"id": 1, "created_at": None, "user": {"login": "testuser"}}
        ]
    }.get(path, [])
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 0
    assert metrics.issue_count == 0

@pytest.mark.anyio
async def test_open_issues(extractor, mock_client):
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo1/issues": [
            {
                "id": 1,
                "created_at": "2026-10-05T10:00:00Z",
                "closed_at": None, # open issue
                "user": {"login": "testuser"}
            }
        ]
    }.get(path, [])
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.issue_count == 1
    assert metrics.issue_resolution_hours is None

@pytest.mark.anyio
async def test_pr_and_reviews(extractor, mock_client):
    def side_effect(path, params=None):
        if path == "repos/org/repo1/issues":
            return [
                {
                    "id": 200,
                    "number": 42,
                    "pull_request": {},
                    "created_at": "2026-10-05T10:00:00Z",
                    "user": {"login": "otheruser"}
                }
            ]
        elif path == "repos/org/repo1/pulls/42/reviews":
            return [
                {
                    "user": {"login": "testuser"},
                    "submitted_at": "2026-10-05T11:00:00Z"
                }
            ]
        return []
        
    mock_client.get_paginated.side_effect = side_effect
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.pull_request_count == 0 # created by otheruser
    assert metrics.review_count == 1
    assert metrics.review_response_hours == 1.0

@pytest.mark.anyio
async def test_missing_or_blank_username_returns_empty_metrics(extractor, mock_client):
    # None or empty username should return zero metrics without making API calls
    metrics = await extractor.extract_weekly_metrics("", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 0
    assert metrics.pull_request_count == 0
    assert metrics.issue_count == 0
    assert mock_client.get_paginated.call_count == 0

    metrics_none = await extractor.extract_weekly_metrics(None, date(2026, 10, 5), date(2026, 10, 11))
    assert metrics_none.github_commit_count == 0
    assert mock_client.get_paginated.call_count == 0

@pytest.mark.anyio
async def test_unauthorized_token_handled_gracefully(extractor, mock_client):
    from app.services.github_client import GitHubUnauthorizedError
    mock_client.get_paginated.side_effect = GitHubUnauthorizedError("Expired or invalid token")
    
    # Should not raise exception; handles gracefully and returns collected/zero metrics
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 0
    assert metrics.pull_request_count == 0

@pytest.mark.anyio
async def test_inaccessible_repository_handled_gracefully(extractor, mock_client):
    from app.services.github_client import GitHubNotFoundError
    extractor.repos = ["org/private_or_deleted_repo", "org/valid_repo"]

    def side_effect(path, params=None):
        if "private_or_deleted_repo" in path:
            raise GitHubNotFoundError("Repository not found")
        elif "valid_repo/commits" in path:
            return [{"sha": "valid_sha", "commit": {"author": {"date": "2026-10-05T10:00:00Z"}}}]
        return []

    mock_client.get_paginated.side_effect = side_effect
    
    # Should catch 404 on first repo and proceed to extract from valid_repo without crashing
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    assert metrics.github_commit_count == 1

