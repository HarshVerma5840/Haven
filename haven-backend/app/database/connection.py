from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

engine_args = {}
if settings.database_url.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    engine_args["pool_size"] = 5
    engine_args["max_overflow"] = 10

engine = create_engine(settings.database_url, **engine_args)

identity_engine_args = {}
if settings.identity_database_url.startswith("sqlite"):
    identity_engine_args["connect_args"] = {"check_same_thread": False}
else:
    identity_engine_args["pool_size"] = 5
    identity_engine_args["max_overflow"] = 10

identity_engine = create_engine(settings.identity_database_url, **identity_engine_args)

behavioral_engine_args = {}
if settings.behavioral_database_url.startswith("sqlite"):
    behavioral_engine_args["connect_args"] = {"check_same_thread": False}
else:
    behavioral_engine_args["pool_size"] = 5
    behavioral_engine_args["max_overflow"] = 10

behavioral_engine = create_engine(settings.behavioral_database_url, **behavioral_engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
IdentitySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=identity_engine)
BehavioralSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=behavioral_engine)
