import pytest
from app.services.identity_service import IdentityService

def test_deterministic_hashing():
    service = IdentityService(salt="test_salt_123")
    hash1 = service.hash_identity("john.doe@example.com")
    hash2 = service.hash_identity("john.doe@example.com")
    hash3 = service.hash_identity("  John.Doe@Example.com ") # Should normalize
    
    assert hash1 == hash2
    assert hash1 == hash3

def test_different_identifiers_different_hashes():
    service = IdentityService(salt="test_salt_123")
    hash1 = service.hash_identity("john.doe@example.com")
    hash2 = service.hash_identity("jane.doe@example.com")
    
    assert hash1 != hash2

def test_different_salts_different_hashes():
    service1 = IdentityService(salt="test_salt_123")
    service2 = IdentityService(salt="test_salt_456")
    
    hash1 = service1.hash_identity("john.doe@example.com")
    hash2 = service2.hash_identity("john.doe@example.com")
    
    assert hash1 != hash2

def test_empty_input_rejection():
    service = IdentityService(salt="test_salt_123")
    with pytest.raises(ValueError, match="Identifier cannot be empty"):
        service.hash_identity("")
        
    with pytest.raises(ValueError, match="Identifier cannot be empty"):
        service.hash_identity("   ")
        
    with pytest.raises(ValueError, match="Identifier cannot be empty"):
        service.hash_identity(None)

def test_no_raw_identifier_in_hash():
    service = IdentityService(salt="test_salt_123")
    identifier = "john.doe@example.com"
    hashed = service.hash_identity(identifier)
    
    assert identifier not in hashed
    assert "john" not in hashed

def test_stable_output_length_and_format():
    service = IdentityService(salt="test_salt_123")
    hashed = service.hash_identity("john.doe@example.com")
    
    # HMAC-SHA256 hexdigest is always 64 characters long
    assert len(hashed) == 64
    
    # Verify it is hex
    int(hashed, 16) # Will raise ValueError if not valid hex
