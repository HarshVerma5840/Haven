import pytest
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, BehavioralSessionLocal
from app.database import models
from seed import seed_database
import run_migrations

def test_seed_database_idempotent():
    # 1. Run migrations to ensure clean tables
    # Since this is a test, it hits the test database via .env overrides
    # but run_migrations hits the same URLs in config.
    run_migrations.run_migrations()
    
    # 2. Run seed once
    seed_database()
    
    db: Session = SessionLocal()
    b_db = BehavioralSessionLocal()
    
    try:
        # Check counts
        user_count_1 = db.query(models.User).count()
        metrics_count_1 = b_db.query(models.WeeklyEmployeeMetrics).count()
        preds_count_1 = b_db.query(models.BurnoutPrediction).count()
        
        # Ensure we actually inserted data
        assert user_count_1 >= 13
        assert metrics_count_1 >= 9
        assert preds_count_1 >= 9
        
        # 3. Run seed a second time to test idempotency
        seed_database()
        
        user_count_2 = db.query(models.User).count()
        metrics_count_2 = b_db.query(models.WeeklyEmployeeMetrics).count()
        preds_count_2 = b_db.query(models.BurnoutPrediction).count()
        
        # Counts should remain exactly the same
        assert user_count_1 == user_count_2
        assert metrics_count_1 == metrics_count_2
        assert preds_count_1 == preds_count_2
        
    finally:
        db.close()
        b_db.close()
