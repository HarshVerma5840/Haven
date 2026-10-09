from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Haven Backend"
    app_env: str = "development"
    debug: bool = True
    
    database_url: str = "sqlite:///./haven_test.db"
    identity_database_url: str = "sqlite:///./haven_identity.db"
    behavioral_database_url: str = "sqlite:///./haven_behavioral.db"
    
    jwt_secret: str = "test_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    
    vault_salt: str = "test_salt_12345678"
    encryption_key: str = "test_encryption_key_12345678901234567890123"
    haven_encryption_private_key: str = ""
    haven_encryption_key_id: str = "haven-key-2026-01"
    
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]
    
    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_organization: str = ""
    github_repositories: list[str] = []
    github_request_timeout_seconds: int = 30
    github_max_retries: int = 3
    github_working_timezone: str = "UTC"
    github_workday_start: str = "09:00"
    github_workday_end: str = "17:00"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
