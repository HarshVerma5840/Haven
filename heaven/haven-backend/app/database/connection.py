from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

identity_engine = create_engine(
    settings.identity_database_url,
    connect_args={"check_same_thread": False} if settings.identity_database_url.startswith("sqlite") else {}
)

behavioral_engine = create_engine(
    settings.behavioral_database_url,
    connect_args={"check_same_thread": False} if settings.behavioral_database_url.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
IdentitySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=identity_engine)
BehavioralSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=behavioral_engine)
