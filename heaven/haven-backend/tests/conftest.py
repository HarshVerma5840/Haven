import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app as fastapi_app
from app.database.base import Base
import app.database.models as models
from app.dependencies import get_db, get_identity_db, get_behavioral_db

# Separate in-memory SQLite engines
core_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
identity_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
behavioral_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

CoreSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=core_engine)
IdentitySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=identity_engine)
BehavioralSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=behavioral_engine)

@pytest.fixture(scope="session")
def db_engines():
    # Core engine creates all tables for standalone tests
    Base.metadata.create_all(bind=core_engine)
    
    # Specific vaults create their assigned tables
    models.IdentityMapping.__table__.create(bind=identity_engine)
    models.WeeklyEmployeeMetrics.__table__.create(bind=behavioral_engine)
    models.BurnoutPrediction.__table__.create(bind=behavioral_engine)
    
    yield (core_engine, identity_engine, behavioral_engine)
    
    Base.metadata.drop_all(bind=core_engine)
    models.IdentityMapping.__table__.drop(bind=identity_engine)
    models.WeeklyEmployeeMetrics.__table__.drop(bind=behavioral_engine)
    models.BurnoutPrediction.__table__.drop(bind=behavioral_engine)

@pytest.fixture(scope="function")
def db_session(db_engines):
    core, iden, behav = db_engines
    
    conn_core = core.connect()
    conn_iden = iden.connect()
    conn_behav = behav.connect()
    
    trans_core = conn_core.begin()
    trans_iden = conn_iden.begin()
    trans_behav = conn_behav.begin()
    
    session_core = CoreSessionLocal(bind=conn_core)
    session_iden = IdentitySessionLocal(bind=conn_iden)
    session_behav = BehavioralSessionLocal(bind=conn_behav)
    
    # We will yield session_core as the primary "db_session" for user creation in tests
    # But attach the other sessions to it just for teardown convenience
    session_core.iden = session_iden
    session_core.behav = session_behav
    
    yield session_core
    
    session_core.close()
    session_iden.close()
    session_behav.close()
    
    try:
        trans_core.rollback()
    except Exception:
        pass
    try:
        trans_iden.rollback()
    except Exception:
        pass
    try:
        trans_behav.rollback()
    except Exception:
        pass
    
    conn_core.close()
    conn_iden.close()
    conn_behav.close()

    with core.begin() as conn:
        for tbl in reversed(Base.metadata.sorted_tables):
            conn.execute(tbl.delete())
    with iden.begin() as conn:
        conn.execute(models.IdentityMapping.__table__.delete())
    with behav.begin() as conn:
        conn.execute(models.WeeklyEmployeeMetrics.__table__.delete())
        conn.execute(models.BurnoutPrediction.__table__.delete())

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session
    def override_get_identity_db():
        yield db_session.iden
    def override_get_behavioral_db():
        yield db_session.behav
            
    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_identity_db] = override_get_identity_db
    fastapi_app.dependency_overrides[get_behavioral_db] = override_get_behavioral_db
    
    with TestClient(fastapi_app) as test_client:
        yield test_client
        
    fastapi_app.dependency_overrides.clear()
