import hmac
import hashlib
from app.config import get_settings
import structlog

logger = structlog.get_logger(__name__)

class IdentityService:
    def __init__(self, salt: str = None):
        """
        Initializes the IdentityService. 
        Accepts an optional salt for testing, otherwise falls back to the application configuration.
        """
        if salt is not None:
            self.salt = salt.encode('utf-8')
        else:
            settings = get_settings()
            self.salt = settings.vault_salt.encode('utf-8')

    def hash_identity(self, identifier: str) -> str:
        """
        Creates a consistent HMAC-SHA256 hash for an employee identifier (e.g. email or github username).
        Raw employee IDs or emails should NEVER be stored.
        """
        if not identifier or not identifier.strip():
            logger.error("Attempted to hash empty identifier")
            raise ValueError("Identifier cannot be empty")
            
        normalized = identifier.strip().lower().encode('utf-8')
        
        # Use HMAC-SHA256
        hashed = hmac.new(self.salt, normalized, hashlib.sha256).hexdigest()
        
        return hashed
