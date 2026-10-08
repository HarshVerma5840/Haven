import base64
import hashlib
from cryptography.fernet import Fernet
from typing import Optional
from app.config import get_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()

def _get_fernet() -> Fernet:
    """
    Derives a valid 32-byte base64-encoded key from the settings.encryption_key.
    Uses SHA-256 to guarantee 32 bytes length.
    """
    key_bytes = settings.encryption_key.encode('utf-8')
    derived_key = hashlib.sha256(key_bytes).digest()
    b64_key = base64.urlsafe_b64encode(derived_key)
    return Fernet(b64_key)

def encrypt_value(value: Optional[str]) -> Optional[str]:
    """Encrypts a string value. Returns None if input is None or empty."""
    if not value:
        return None
    try:
        f = _get_fernet()
        return f.encrypt(value.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error("Failed to encrypt identity value.")
        raise ValueError("Encryption failed")

def decrypt_value(encrypted_value: Optional[str]) -> Optional[str]:
    """Decrypts a string value. Restricted strictly to identity vault logic."""
    if not encrypted_value:
        return None
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_value.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error("Failed to decrypt identity value.")
        raise ValueError("Decryption failed")
