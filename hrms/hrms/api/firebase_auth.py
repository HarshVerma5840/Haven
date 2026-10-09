import frappe

@frappe.whitelist(allow_guest=True, methods=["POST"])
def login_with_firebase_token(id_token=None):
    frappe.throw("Firebase authentication has been removed.")

@frappe.whitelist(allow_guest=True)
def firebase_config():
    return {"configured": False}

@frappe.whitelist(allow_guest=True)
def firebase_status():
    return {"configured": False, "server_verification_configured": False}
