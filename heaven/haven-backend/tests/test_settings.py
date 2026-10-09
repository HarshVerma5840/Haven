import pytest
from app.config import Settings

def test_github_settings_defaults():
    settings = Settings()
    assert settings.github_token == ""
    assert settings.github_api_base_url == "https://api.github.com"
    assert settings.github_request_timeout_seconds == 30
    assert settings.github_max_retries == 3
    assert settings.github_working_timezone == "UTC"
    assert settings.github_workday_start == "09:00"
    assert settings.github_workday_end == "17:00"
    assert settings.github_organization == ""
    assert settings.github_repositories == []
