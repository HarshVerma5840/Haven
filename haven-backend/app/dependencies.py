from typing import Generator
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, IdentitySessionLocal, BehavioralSessionLocal

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_identity_db() -> Generator[Session, None, None]:
    db = IdentitySessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_behavioral_db() -> Generator[Session, None, None]:
    db = BehavioralSessionLocal()
    try:
        yield db
    finally:
        db.close()
