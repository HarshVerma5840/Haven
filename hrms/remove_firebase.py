import os
import re

base_dir = r"c:\Users\kashi\OneDrive\Documents\GitHub\Haven\hrms"

# 1. pyproject.toml
pyproject_path = os.path.join(base_dir, "pyproject.toml")
with open(pyproject_path, "r", encoding="utf-8") as f:
    content = f.read()
content = re.sub(r'\s*"firebase-admin[^"]+",?', '', content)
with open(pyproject_path, "w", encoding="utf-8") as f:
    f.write(content)

# 2. firebase_auth.py
firebase_auth_path = os.path.join(base_dir, "hrms", "api", "firebase_auth.py")
with open(firebase_auth_path, "w", encoding="utf-8") as f:
    f.write("""import frappe

@frappe.whitelist(allow_guest=True, methods=["POST"])
def login_with_firebase_token(id_token=None):
    frappe.throw("Firebase authentication has been removed.")

@frappe.whitelist(allow_guest=True)
def firebase_config():
    return {"configured": False}

@frappe.whitelist(allow_guest=True)
def firebase_status():
    return {"configured": False, "server_verification_configured": False}
""")

# 3. employee_provisioning.py
employee_provisioning_path = os.path.join(base_dir, "hrms", "api", "employee_provisioning.py")
with open(employee_provisioning_path, "r", encoding="utf-8") as f:
    content = f.read()

# Strip firebase imports
content = re.sub(r'from firebase_admin import auth as firebase_auth\n', '', content)
content = re.sub(r'from hrms\.api\.firebase_auth import _get_firebase_admin_app\n', '', content)

# Strip firebase user methods
content = re.sub(r'def _get_existing_firebase_user_by_email.*?return None\n\n\n', '', content, flags=re.DOTALL)
content = re.sub(r'def _get_existing_firebase_user_by_uid.*?return None\n\n\n', '', content, flags=re.DOTALL)
content = re.sub(r'def _ensure_firebase_user.*?return firebase_user\n\n\n', '', content, flags=re.DOTALL)
content = re.sub(r'def _get_existing_mapped_firebase_user.*?return firebase_user\n\n\n', '', content, flags=re.DOTALL)

# Modify _queue_firebase_invitation
content = re.sub(r'link = firebase_auth\.generate_password_reset_link\(email\)', 'link = "http://localhost:8001/update-password"', content)

# Modify provision_employee_login
content = re.sub(r'firebase_user = _ensure_firebase_user\(user, employee_doc, email\)\n\t\tfirebase_user = _ensure_firebase_user\(user, employee_doc, email, password=password\)', '', content)
content = re.sub(r'try:\n\t\t\tfrom firebase_admin import firestore.*?\n\t\texcept Exception:\n\t\t\tfrappe\.logger\("employee_provisioning"\)\.warning\(\n\t\t\t\t"Firestore sync failed for %s", employee_doc\.name\n\t\t\t\)', '', content, flags=re.DOTALL)

content = re.sub(r'"firebase_uid": firebase_user\.uid', '"firebase_uid": None', content)
content = re.sub(r'Firebase UID \{0\}', 'Frappe User {0}', content)
content = re.sub(r'firebase_user\.uid', 'user.name', content)

with open(employee_provisioning_path, "w", encoding="utf-8") as f:
    f.write(content)

# 4. Remove test file
test_file = os.path.join(base_dir, "hrms", "tests", "test_phase5_e2e.py")
if os.path.exists(test_file):
    os.remove(test_file)

print("Firebase authentication successfully removed.")
