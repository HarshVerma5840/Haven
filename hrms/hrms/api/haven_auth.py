import time
import uuid
import jwt
import frappe
from frappe import _

HR_ADMIN_ROLES = {"Administrator", "HR Manager", "System Manager"}
HR_MANAGER_ROLES = {"HR User"}


def get_mapped_haven_role(user: str | None = None) -> str | None:
	"""Check permissions and return the mapped Haven role ('HR_ADMIN' or 'MANAGER').

	Returns None if the user does not possess an approved HR role.
	"""
	if not user:
		user = frappe.session.user
	if not user or user == "Guest":
		return None
	if user == "Administrator":
		return "HR_ADMIN"

	user_roles = set(frappe.get_roles(user))
	if HR_ADMIN_ROLES.intersection(user_roles):
		return "HR_ADMIN"
	if HR_MANAGER_ROLES.intersection(user_roles):
		return "MANAGER"
	return None


def generate_sso_exchange_token(user: str | None = None) -> str:
	"""Generate a short-lived, signed one-time SSO exchange token for an approved HR user.

	The token has a 60-second expiration, a unique cryptographic nonce (jti),
	and is signed using HS256 with the shared Haven SSO secret.
	"""
	if not user:
		user = frappe.session.user

	mapped_role = get_mapped_haven_role(user)
	if not mapped_role:
		frappe.throw(
			_("Unauthorized: Only approved HR users can generate a Haven exchange token."),
			frappe.PermissionError,
		)

	secret = (
		frappe.conf.get("haven_sso_secret")
		or frappe.conf.get("haven_jwt_secret")
		or "test_secret"
	)
	now = int(time.time())
	payload = {
		"sub": user,
		"username": user,
		"role": mapped_role,
		"jti": str(uuid.uuid4()),
		"type": "sso_exchange",
		"iss": "hrms",
		"aud": "haven",
		"iat": now,
		"exp": now + 60,  # Short-lived: 60 seconds
	}

	return jwt.encode(payload, secret, algorithm="HS256")


@frappe.whitelist()
def get_sso_exchange_token():
	"""Whitelisted Frappe API endpoint for authenticated HR users to request an exchange token."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Authentication required."), frappe.AuthenticationError)

	token = generate_sso_exchange_token(user)
	return {"exchange_token": token}
