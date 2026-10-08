from app.database.models import IdentityMapping
from app.schemas.vault import IdentityMappingCreate
from app.services.identity_vault_service import IdentityVaultService
from app.database.repositories.identity_vault_repository import IdentityVaultRepository
from app.services.identity_service import IdentityService
from app.security.encryption import encrypt_value

def test_encryption_decryption_works_correctly(db_session):
    repo = IdentityVaultRepository(db_session)
    identity_service = IdentityService()
    service = IdentityVaultService(repo, identity_service)
    
    # Create via service (which encrypts)
    mapping_in = IdentityMappingCreate(email="secret@example.com")
    result = service.create_mapping(mapping_in)
    
    # Service returns decrypted email
    assert result.email == "secret@example.com"
    
    # Check raw DB value
    raw_mapping = db_session.query(IdentityMapping).filter(IdentityMapping.employee_hash == result.employee_hash).first()
    assert raw_mapping.email != "secret@example.com"
    assert len(raw_mapping.email) > 20 # Fernet tokens are long
