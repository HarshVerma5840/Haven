import os
from pathlib import Path

base = Path("D:/Haven/haven-backend")
base.mkdir(parents=True, exist_ok=True)

def write_file(path: str, content: str):
    p = base / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.strip() + "\n", encoding="utf-8")

# app/__init__.py
write_file("app/__init__.py", "")
write_file("app/api/__init__.py", "")
write_file("app/database/__init__.py", "")
write_file("app/schemas/__init__.py", "")
write_file("app/services/__init__.py", "")
write_file("app/security/__init__.py", "")
write_file("app/observability/__init__.py", "")

# app/config.py
write_file("app/config.py", """
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Haven Backend"
    app_env: str = "development"
    debug: bool = True
    
    database_url: str = "sqlite:///./haven_test.db"
    
    jwt_secret: str = "test_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    
    vault_salt: str = "test_salt_12345678"
    encryption_key: str = "test_encryption_key_12345678901234567890123"
    
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
""")

# app/observability/logging.py
write_file("app/observability/logging.py", """
import structlog
import logging
import sys

def setup_logging(log_level: str = "INFO"):
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=getattr(logging, log_level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()
""")

# app/database/base.py
write_file("app/database/base.py", """
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
""")

# app/database/models.py
write_file("app/database/models.py", """
from sqlalchemy import Column, String, Date, Integer, Float, CheckConstraint, UniqueConstraint, DateTime, func
from .base import Base

class WeeklyEmployeeMetrics(Base):
    __tablename__ = 'weekly_employee_metrics'

    id = Column(Integer, primary_key=True, index=True)
    employee_hash = Column(String, nullable=False)
    week_start_date = Column(Date, nullable=False)
    
    department = Column(String)
    designation = Column(String)
    employment_type = Column(String)
    tenure_months = Column(Integer)
    team_size = Column(Integer)
    
    avg_daily_work_hours = Column(Float)
    overtime_hours = Column(Float)
    
    late_entry_count = Column(Integer)
    early_exit_count = Column(Integer)
    missing_checkout_count = Column(Integer)
    weekend_work_days = Column(Integer)
    holiday_work_days = Column(Integer)
    consecutive_work_days = Column(Integer)
    night_shift_count = Column(Integer)
    shift_change_count = Column(Integer)
    
    leave_days_taken = Column(Integer)
    unused_leave_balance = Column(Float)
    unplanned_leave_count = Column(Integer)
    leave_cancellation_count = Column(Integer)
    
    timesheet_hours = Column(Float)
    timesheet_correction_count = Column(Integer)
    workload_change_percent = Column(Float)
    
    github_commit_count = Column(Integer)
    after_hours_commit_count = Column(Integer)
    weekend_commit_count = Column(Integer)
    pull_request_count = Column(Integer)
    review_count = Column(Integer)
    review_response_hours = Column(Float)
    issue_count = Column(Integer)
    issue_resolution_hours = Column(Float)
    
    appraisal_rating = Column(Float)
    goal_completion_percent = Column(Float)
    
    grievance_count = Column(Integer)
    grievance_resolution_days = Column(Float)
    travel_days = Column(Integer)
    payroll_issue_count = Column(Integer)
    
    burnout_score = Column(Float)
    burnout_risk = Column(String)
    
    schema_version = Column(String, nullable=False)
    data_completeness = Column(Float)
    source_timestamp = Column(DateTime)
    label_source = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('employee_hash', 'week_start_date', name='uq_employee_week'),
        CheckConstraint('burnout_score >= 0.0 AND burnout_score <= 1.0', name='chk_burnout_score'),
        CheckConstraint('appraisal_rating >= 1.0 AND appraisal_rating <= 5.0', name='chk_appraisal_rating'),
        CheckConstraint('team_size >= 0', name='chk_team_size'),
        CheckConstraint('tenure_months >= 0', name='chk_tenure_months'),
        CheckConstraint('avg_daily_work_hours >= 0', name='chk_avg_daily_work_hours'),
        CheckConstraint('overtime_hours >= 0', name='chk_overtime_hours'),
        CheckConstraint('late_entry_count >= 0', name='chk_late_entry_count'),
        CheckConstraint('early_exit_count >= 0', name='chk_early_exit_count'),
        CheckConstraint('missing_checkout_count >= 0', name='chk_missing_checkout_count'),
        CheckConstraint('weekend_work_days >= 0', name='chk_weekend_work_days'),
        CheckConstraint('holiday_work_days >= 0', name='chk_holiday_work_days'),
        CheckConstraint('consecutive_work_days >= 0', name='chk_consecutive_work_days'),
        CheckConstraint('night_shift_count >= 0', name='chk_night_shift_count'),
        CheckConstraint('shift_change_count >= 0', name='chk_shift_change_count'),
        CheckConstraint('leave_days_taken >= 0', name='chk_leave_days_taken'),
        CheckConstraint('unplanned_leave_count >= 0', name='chk_unplanned_leave_count'),
        CheckConstraint('leave_cancellation_count >= 0', name='chk_leave_cancellation_count'),
        CheckConstraint('timesheet_hours >= 0', name='chk_timesheet_hours'),
        CheckConstraint('timesheet_correction_count >= 0', name='chk_timesheet_correction_count'),
        CheckConstraint('github_commit_count >= 0', name='chk_github_commit_count'),
        CheckConstraint('after_hours_commit_count >= 0', name='chk_after_hours_commit_count'),
        CheckConstraint('weekend_commit_count >= 0', name='chk_weekend_commit_count'),
        CheckConstraint('pull_request_count >= 0', name='chk_pull_request_count'),
        CheckConstraint('review_count >= 0', name='chk_review_count'),
        CheckConstraint('review_response_hours >= 0', name='chk_review_response_hours'),
        CheckConstraint('issue_count >= 0', name='chk_issue_count'),
        CheckConstraint('issue_resolution_hours >= 0', name='chk_issue_resolution_hours'),
        CheckConstraint('grievance_count >= 0', name='chk_grievance_count'),
        CheckConstraint('grievance_resolution_days >= 0', name='chk_grievance_resolution_days'),
        CheckConstraint('travel_days >= 0', name='chk_travel_days'),
        CheckConstraint('payroll_issue_count >= 0', name='chk_payroll_issue_count'),
    )
""")

# app/database/connection.py
write_file("app/database/connection.py", """
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
""")

# app/dependencies.py
write_file("app/dependencies.py", """
from typing import Generator
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
""")

# app/schemas/common.py
write_file("app/schemas/common.py", """
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    version: str | None = None
    
class ReadyResponse(BaseModel):
    status: str
    database: str
""")

# app/api/health.py
write_file("app/api/health.py", """
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas.common import HealthResponse, ReadyResponse
from app.dependencies import get_db

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "version": "1.0"}

@router.get("/ready", response_model=ReadyResponse)
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed")
    
    return {"status": "ok", "database": db_status}
""")

# app/main.py
write_file("app/main.py", """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health
from app.config import get_settings
from app.observability.logging import setup_logging
import structlog
from contextlib import asynccontextmanager

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger = setup_logging(settings.log_level)
    logger.info("Starting Haven Backend", env=settings.app_env)
    yield
    # Shutdown logic
    logger.info("Shutting down Haven Backend")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
""")

# tests/conftest.py
write_file("tests/conftest.py", """
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database.base import Base
from app.dependencies import get_db

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
""")

# tests/test_health.py
write_file("tests/test_health.py", """
from app.config import get_settings

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
""")

# tests/test_models.py
write_file("tests/test_models.py", """
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
""")

# pyproject.toml
write_file("pyproject.toml", """
[project]
name = "haven-backend"
version = "1.0.0"
description = "Haven FastAPI Backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.128.6",
    "uvicorn[standard]>=0.40.0",
    "sqlalchemy>=2.0.46",
    "alembic>=1.18.3",
    "pydantic[email]>=2.12.5",
    "pydantic-settings>=2.13.1",
    "structlog>=25.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
""")

# README.md
write_file("README.md", """
# Haven Backend

This is the FastAPI backend for Haven. It provides a production-oriented foundation with structured logging, configuration management, database connections, and basic health checks.

## Development Setup

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

**Windows:**
```bash
venv\\Scripts\\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Fill in the necessary values. The application will use safe defaults for development if certain values are omitted, but will fail if required production secrets are missing in a production environment.

### 5. Run Alembic migrations

Initialize the database schema:
```bash
alembic upgrade head
```

### 6. Run the API

```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

### 7. Run tests

```bash
pytest
```
""")

print("Bootstrapping complete.")
