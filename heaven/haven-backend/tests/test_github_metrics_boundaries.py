import pytest
from datetime import date
from unittest.mock import AsyncMock

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
    settings.github_repositories = ["org/repo"]
    settings.github_working_timezone = "UTC" # test in UTC first
    return GitHubMetricsExtractor(mock_client)

@pytest.mark.anyio
async def test_week_boundaries_inclusion(extractor, mock_client):
    """
    Events exactly at 00:00:00 of the start_date and 23:59:59 of end_date
    should be included.
    """
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo/commits": [
            # Exactly start boundary
            {"sha": "1", "commit": {"author": {"date": "2026-10-05T00:00:00Z"}}},
            # Exactly end boundary
            {"sha": "2", "commit": {"author": {"date": "2026-10-11T23:59:59Z"}}},
            # One second before start
            {"sha": "3", "commit": {"author": {"date": "2026-10-04T23:59:59Z"}}},
            # One second after end
            {"sha": "4", "commit": {"author": {"date": "2026-10-12T00:00:00Z"}}}
        ],
        "repos/org/repo/issues": []
    }.get(path, [])
    
    metrics = await extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    
    # Only sha 1 and 2 should be included
    assert metrics.github_commit_count == 2
    # 00:00:00 is after-hours, 23:59:59 is after-hours
    assert metrics.after_hours_commit_count == 2

@pytest.mark.anyio
async def test_timezone_boundaries(mock_client):
    """
    Test that configured timezone shifts the bounds appropriately.
    If timezone is America/New_York (UTC-4/5), start_date 00:00 local is +4/+5 UTC.
    """
    settings = get_settings()
    settings.github_repositories = ["org/repo"]
    settings.github_working_timezone = "America/New_York"
    
    tz_extractor = GitHubMetricsExtractor(mock_client)
    
    mock_client.get_paginated.side_effect = lambda path, params=None: {
        "repos/org/repo/commits": [
            # 00:00 UTC on start_date is actually the previous day in EST/EDT, so it shouldn't be included.
            {"sha": "utc_midnight", "commit": {"author": {"date": "2026-10-05T00:00:00Z"}}},
            # 04:00 UTC on 2026-10-05 is exactly 00:00 EDT (Oct 5 is EDT). This SHOULD be included.
            {"sha": "edt_midnight", "commit": {"author": {"date": "2026-10-05T04:00:00Z"}}},
        ],
        "repos/org/repo/issues": []
    }.get(path, [])
    
    metrics = await tz_extractor.extract_weekly_metrics("testuser", date(2026, 10, 5), date(2026, 10, 11))
    
    assert metrics.github_commit_count == 1
