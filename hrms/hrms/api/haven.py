import frappe
from frappe import _
import json
from datetime import datetime

@frappe.whitelist()
def get_weekly_metrics():
    """
    Returns weekly employee metrics encrypted with the Haven public key.
    """
    # This is a stub for retrieving metrics
    metrics = [
        {"employee_hash": "sample-hash", "avg_daily_work_hours": 8.0, "department": "Engineering"}
    ]
    
    public_key_pem = frappe.conf.get("haven_public_key")
    key_id = frappe.conf.get("haven_key_id", "haven-key-2026-01")
    
    if not public_key_pem:
        frappe.throw(_("HAVEN_PUBLIC_KEY is not configured in site config."))
        
    try:
        from jwcrypto import jwk, jwe
    except ImportError:
        frappe.throw(_("jwcrypto library is not installed."))
        
    try:
        key = jwk.JWK.from_pem(public_key_pem.encode('utf-8'))
        
        payload = json.dumps(metrics)
        protected_header = {
            "alg": "RSA-OAEP-256",
            "enc": "A256GCM",
            "kid": key_id
        }
        
        jwetoken = jwe.JWE(payload.encode('utf-8'), recipient=key, protected=protected_header)
        enc = jwetoken.serialize(compact=False)
        enc_dict = json.loads(enc)
        
        return {
            "key_id": key_id,
            "algorithm": "RSA-OAEP-256+A256GCM",
            "encrypted_key": enc_dict.get("encrypted_key", ""),
            "iv": enc_dict.get("iv", ""),
            "ciphertext": enc_dict.get("ciphertext", ""),
            "tag": enc_dict.get("tag", ""),
            "schema_version": "1.0",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    except Exception as e:
        frappe.throw(_("Encryption failed: {0}").format(str(e)))
