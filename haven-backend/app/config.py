from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Haven Backend"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/haven"
    identity_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/haven_identity"
    behavioral_database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/haven_behavioral"

    model_dir: str = ""

    jwt_secret: str = "test_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    vault_salt: str = "test_salt_12345678"
    encryption_key: str = "test_encryption_key_12345678901234567890123"
    haven_encryption_private_key: str = ""
    haven_encryption_key_id: str = "haven-key-2026-01"

    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]

    service_token: str = "default_dev_service_token_replace_in_prod"

    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_organization: str = ""
    github_repositories: list[str] | str = []
    github_request_timeout_seconds: int = 30
    github_max_retries: int = 3
    github_working_timezone: str = "UTC"
    github_workday_start: str = "09:00"
    github_workday_end: str = "17:00"

    @field_validator("github_repositories", mode="after")
    @classmethod
    def parse_github_repositories(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [repo.strip() for repo in v.split(",") if repo.strip()]
        return v or []

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_prediction: int = 3600 # 1 hour
    cache_ttl_dashboard: int = 300 # 5 minutes
    cache_ttl_analytics: int = 86400 # 24 hours

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
