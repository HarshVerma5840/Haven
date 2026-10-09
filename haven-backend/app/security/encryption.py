import os
from typing import Dict, Any, Optional
from jwcrypto import jwk, jwe
import json
from cryptography.fernet import Fernet
import base64

def get_fernet() -> Fernet:
    from app.config import get_settings
    settings = get_settings()
    key = settings.encryption_key.encode('utf-8')
    # Fernet requires a 32 url-safe base64-encoded byte string
    if len(key) < 32:
        key = key.ljust(32, b'0')
    elif len(key) > 32:
        key = key[:32]
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    f = get_fernet()
    return f.encrypt(value.encode('utf-8')).decode('utf-8')

def decrypt_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    f = get_fernet()
    return f.decrypt(value.encode('utf-8')).decode('utf-8')

def get_private_key() -> jwk.JWK:
    from app.config import get_settings
    settings = get_settings()
    pem = settings.haven_encryption_private_key
    if not pem:
        raise ValueError("HAVEN_ENCRYPTION_PRIVATE_KEY is not set.")
    return jwk.JWK.from_pem(pem.encode('utf-8'))

def decrypt_jwe(jwe_token: str) -> Dict[str, Any]:
    key = get_private_key()
    jwetoken = jwe.JWE()
    try:
        jwetoken.deserialize(jwe_token, key=key)
        payload = jwetoken.payload.decode('utf-8')
        return json.loads(payload)
    except Exception as e:
        raise ValueError(f"Failed to decrypt JWE token: {e}")
