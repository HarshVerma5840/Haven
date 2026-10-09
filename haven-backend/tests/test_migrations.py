import pytest
from sqlalchemy import create_engine, inspect
from app.config import get_settings
import run_migrations

def test_targeted_migrations_create_correct_tables():
    settings = get_settings()
    
    # Run the migrations (hitting the test databases as defined in conftest and env overrides)
    run_migrations.run_migrations()
    
    # Inspect Core Database
    core_engine = create_engine(settings.database_url)
    core_inspector = inspect(core_engine)
    core_tables = core_inspector.get_table_names()
    assert 'users' in core_tables
    assert 'alembic_version' in core_tables
    assert 'identity_mappings' not in core_tables
    assert 'weekly_employee_metrics' not in core_tables
    
    # Inspect Identity Database
    iden_engine = create_engine(settings.identity_database_url)
    iden_inspector = inspect(iden_engine)
    iden_tables = iden_inspector.get_table_names()
    assert 'identity_mappings' in iden_tables
    assert 'alembic_version' in iden_tables
    assert 'users' not in iden_tables
    assert 'weekly_employee_metrics' not in iden_tables
    
    # Inspect Behavioral Database
    behav_engine = create_engine(settings.behavioral_database_url)
    behav_inspector = inspect(behav_engine)
    behav_tables = behav_inspector.get_table_names()
    assert 'weekly_employee_metrics' in behav_tables
    assert 'burnout_predictions' in behav_tables
    assert 'alembic_version' in behav_tables
    assert 'users' not in behav_tables
    assert 'identity_mappings' not in behav_tables
