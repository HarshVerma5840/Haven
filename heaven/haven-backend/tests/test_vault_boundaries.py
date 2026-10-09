import pytest
from sqlalchemy.exc import OperationalError

from app.database.repositories.identity_vault_repository import IdentityVaultRepository
from app.database.repositories.behavioral_vault_repository import BehavioralVaultRepository
from app.database.models import BurnoutPrediction, IdentityMapping

def test_identity_repo_cannot_access_behavioral_data(db_session):
    """Prove that Identity Vault DB connection has no burnout_predictions table."""
    iden_db = db_session.iden
    repo = IdentityVaultRepository(iden_db)
    
    with pytest.raises(OperationalError) as exc_info:
        # Attempt to query BurnoutPrediction on identity DB
        iden_db.query(BurnoutPrediction).all()
        
    assert "no such table: burnout_predictions" in str(exc_info.value)

def test_behavioral_repo_cannot_access_identity_data(db_session):
    """Prove that Behavioral Vault DB connection has no identity_mappings table."""
    behav_db = db_session.behav
    repo = BehavioralVaultRepository(behav_db)
    
    with pytest.raises(OperationalError) as exc_info:
        # Attempt to query IdentityMapping on behavioral DB
        behav_db.query(IdentityMapping).all()
        
    assert "no such table: identity_mappings" in str(exc_info.value)
