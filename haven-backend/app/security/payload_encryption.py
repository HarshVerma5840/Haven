import json
import base64
from jwcrypto import jwk, jwe
from app.config import get_settings

settings = get_settings()

def decrypt_payload(encrypted_payload: dict) -> dict:
    """
    Decrypts a JWE payload using the Haven private key.
    The payload is expected to match the custom envelope format.
    """
    private_key_pem = settings.haven_encryption_private_key
    if not private_key_pem:
        raise ValueError("HAVEN_ENCRYPTION_PRIVATE_KEY is not set")
    
    key = jwk.JWK.from_pem(private_key_pem.encode('utf-8'))
    
    # Reconstruct the JWE flattened JSON serialization
    alg_enc = encrypted_payload.get("algorithm", "RSA-OAEP-256+A256GCM")
    if alg_enc == "RSA-OAEP-256+A256GCM":
        alg = "RSA-OAEP-256"
        enc = "A256GCM"
    else:
        alg = "RSA-OAEP-256"
        enc = "A256GCM"
        
    protected_header = {
        "alg": alg,
        "enc": enc,
        "kid": encrypted_payload.get("key_id")
    }
    
    # Base64url encode the protected header
    protected_b64 = base64.urlsafe_b64encode(json.dumps(protected_header).encode('utf-8')).decode('utf-8').rstrip("=")
    
    jwe_dict = {
        "protected": protected_b64,
        "encrypted_key": encrypted_payload.get("encrypted_key"),
        "iv": encrypted_payload.get("iv"),
        "ciphertext": encrypted_payload.get("ciphertext"),
        "tag": encrypted_payload.get("tag")
    }
    
    jwe_token = jwe.JWE()
    jwe_token.deserialize(json.dumps(jwe_dict))
    jwe_token.decrypt(key)
    
    payload = jwe_token.payload
    return json.loads(payload.decode('utf-8'))
