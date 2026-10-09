import frappe
from frappe import _

no_cache = 1

HR_APPROVED_ROLES = {"HR Manager", "HR User", "System Manager"}


def is_hr_user(user: str | None = None) -> bool:
	"""Check if user has approved HR roles.

	Only users with 'HR Manager', 'HR User', 'System Manager', or 'Administrator'
	are permitted to access Haven. Standard employees and non-HR users return False.
	"""
	if not user:
		user = frappe.session.user
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))
	return bool(HR_APPROVED_ROLES.intersection(user_roles))


def get_context(context):
	"""Server-side entry point for /heaven and /heaven/app/.

	Enforces HR-only access control, redirects unauthenticated/unauthorized users,
	and provides session and CSRF context to the Haven Vue frontend.
	"""
	user = frappe.session.user

	# 1. Unauthenticated users -> redirect to login
	if not user or user == "Guest":
		target_path = frappe.request.path or "/heaven/app/"
		frappe.local.flags.redirect_location = f"/login?redirect-to={target_path}"
		raise frappe.Redirect

	# 2. Employees and non-HR users -> redirect to HRMS Desk (/app)
	if not is_hr_user(user):
		frappe.local.flags.redirect_location = "/app"
		raise frappe.Redirect

	# 3. Base /heaven path -> redirect to /heaven/app/
	request_path = (frappe.request.path or "").rstrip("/")
	if request_path in ("/heaven", ""):
		frappe.local.flags.redirect_location = "/heaven/app/"
		raise frappe.Redirect

	# 4. Context for authenticated HR user
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosempgrep

	context.no_cache = 1
	context.csrf_token = csrf_token
	context.site_name = frappe.local.site
	context.user = user
	context.user_roles = frappe.get_roles(user)
	context.is_hr_user = True

	try:
		from hrms.api.haven_auth import generate_sso_exchange_token
		context.exchange_token = generate_sso_exchange_token(user)
	except Exception:
		context.exchange_token = ""

	return context
