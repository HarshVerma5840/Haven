import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
	sys.path.insert(0, repo_root)

# Mock frappe module if running outside Frappe bench environment
if "frappe" not in sys.modules:
	mock_frappe_mod = MagicMock()
	mock_frappe_mod.__path__ = []
	for mod in ["frappe", "frappe.model", "frappe.model.workflow", "frappe.utils", "frappe.sessions", "frappe.query_builder"]:
		sys.modules[mod] = mock_frappe_mod

if "erpnext" not in sys.modules:
	mock_erp = MagicMock()
	mock_erp.__path__ = []
	sys.modules["erpnext"] = mock_erp
	sys.modules["erpnext.setup.doctype.employee.employee"] = MagicMock()

mock_hr_utils = MagicMock()
mock_hr_utils.check_app_permission.return_value = True
sys.modules["hrms.hr.utils"] = mock_hr_utils

from hrms.boot import is_hr_user as boot_is_hr_user, patch_app_data
from hrms.www.heaven import is_hr_user as www_is_hr_user, get_context
import hrms.hooks as hooks


class TestHavenDeskIntegration(unittest.TestCase):
	"""Integration and unit tests for Haven HR-only Desk integration."""

	def test_is_hr_user_permissions(self):
		"""Verify that only approved HR roles can access Haven."""
		mock_frappe = MagicMock()
		mock_frappe.session.user = "admin@example.com"

		# Administrator
		with patch("hrms.boot.frappe", mock_frappe), patch("hrms.www.heaven.frappe", mock_frappe):
			mock_frappe.session.user = "Administrator"
			self.assertTrue(boot_is_hr_user())
			self.assertTrue(www_is_hr_user())

			# Guest
			mock_frappe.session.user = "Guest"
			self.assertFalse(boot_is_hr_user())
			self.assertFalse(www_is_hr_user())

			# HR Manager
			mock_frappe.session.user = "hr_manager@example.com"
			mock_frappe.get_roles.return_value = ["HR Manager", "Employee", "All"]
			self.assertTrue(boot_is_hr_user())
			self.assertTrue(www_is_hr_user())

			# HR User
			mock_frappe.session.user = "hr_user@example.com"
			mock_frappe.get_roles.return_value = ["HR User", "Employee", "All"]
			self.assertTrue(boot_is_hr_user())
			self.assertTrue(www_is_hr_user())

			# System Manager
			mock_frappe.session.user = "sysadmin@example.com"
			mock_frappe.get_roles.return_value = ["System Manager", "All"]
			self.assertTrue(boot_is_hr_user())
			self.assertTrue(www_is_hr_user())

			# Standard Employee (MUST BE BLOCKED)
			mock_frappe.session.user = "john.doe@example.com"
			mock_frappe.get_roles.return_value = ["Employee", "All"]
			self.assertFalse(boot_is_hr_user())
			self.assertFalse(www_is_hr_user())

			# Non-HR user / Website User (MUST BE BLOCKED)
			mock_frappe.session.user = "vendor@example.com"
			mock_frappe.get_roles.return_value = ["Website User", "All"]
			self.assertFalse(boot_is_hr_user())
			self.assertFalse(www_is_hr_user())

	def test_desk_app_data_hr_user(self):
		"""Verify that HR users see both HR and Haven app icons side-by-side."""
		mock_frappe = MagicMock()
		mock_frappe.session.user = "hr_admin@example.com"
		mock_frappe.get_roles.return_value = ["HR Manager", "Employee"]

		bootinfo = MagicMock()
		bootinfo.app_data = [
			{
				"app_name": "heaven",
				"name": "heaven",
				"title": "Haven",
				"route": "/heaven/app/",
				"sequence_id": 2,
				"on_apps_screen": True,
			},
			{
				"app_name": "erpnext",
				"on_apps_screen": True,
			},
		]
		bootinfo.dock = {}

		with patch("hrms.boot.frappe", mock_frappe):
			patch_app_data(bootinfo)

			# ERPNext hidden
			erp = next(a for a in bootinfo.app_data if a.get("app_name") == "erpnext")
			self.assertFalse(erp["on_apps_screen"])

			# Haven tile active and configured
			haven = next(a for a in bootinfo.app_data if a.get("app_name") == "heaven")
			self.assertTrue(haven["on_apps_screen"])
			self.assertEqual(haven["title"], "Haven")
			self.assertEqual(haven["route"], "/heaven/app/")
			self.assertEqual(haven["sequence_id"], 2)

			# HR tile active and configured beside Haven
			hr = next(a for a in bootinfo.app_data if a.get("app_name") == "hrms")
			self.assertTrue(hr["on_apps_screen"])
			self.assertEqual(hr["sequence_id"], 1)

	def test_desk_app_data_employee_user(self):
		"""Verify that standard employees CANNOT see the Haven icon on Desk."""
		mock_frappe = MagicMock()
		mock_frappe.session.user = "employee@example.com"
		mock_frappe.get_roles.return_value = ["Employee", "All"]

		bootinfo = MagicMock()
		bootinfo.app_data = [
			{
				"app_name": "heaven",
				"name": "heaven",
				"title": "Haven",
				"route": "/heaven/app/",
				"sequence_id": 2,
				"on_apps_screen": True,
			}
		]
		bootinfo.dock = {}

		with patch("hrms.boot.frappe", mock_frappe):
			patch_app_data(bootinfo)

			haven = next(a for a in bootinfo.app_data if a.get("app_name") == "heaven")
			# Must be HIDDEN from apps screen for standard employee
			self.assertFalse(haven["on_apps_screen"])
			self.assertFalse(bootinfo.has_haven_permission)

	def test_server_side_direct_navigation_protection(self):
		"""Verify that direct URLs to /heaven/app/ are protected server-side."""
		mock_frappe = MagicMock()

		# Case 1: Guest -> Redirect to login
		mock_frappe.session.user = "Guest"
		mock_frappe.request.path = "/heaven/app/burnout"
		mock_frappe.Redirect = Exception

		with patch("hrms.www.heaven.frappe", mock_frappe):
			with self.assertRaises(Exception):
				get_context(MagicMock())
			self.assertTrue(
				mock_frappe.local.flags.redirect_location.startswith("/login?redirect-to=")
			)

		# Case 2: Employee user -> Redirect to HRMS Desk (/app)
		mock_frappe.session.user = "emp@example.com"
		mock_frappe.get_roles.return_value = ["Employee", "All"]
		mock_frappe.request.path = "/heaven/app/dashboard"

		with patch("hrms.www.heaven.frappe", mock_frappe):
			with self.assertRaises(Exception):
				get_context(MagicMock())
			self.assertEqual(mock_frappe.local.flags.redirect_location, "/app")

		# Case 3: HR User -> Allowed, gets context
		mock_frappe.session.user = "hr@example.com"
		mock_frappe.get_roles.return_value = ["HR User", "Employee"]
		mock_frappe.request.path = "/heaven/app/"
		mock_frappe.sessions.get_csrf_token.return_value = "token123"
		mock_frappe.local.site = "site1"
		mock_frappe.conf.get.return_value = "test_secret"

		with patch("hrms.www.heaven.frappe", mock_frappe), patch("hrms.api.haven_auth.frappe", mock_frappe):
			ctx = MagicMock()
			result = get_context(ctx)
			self.assertTrue(result.is_hr_user)
			self.assertEqual(result.csrf_token, "token123")
			self.assertTrue(bool(result.exchange_token))

	def test_hooks_configuration(self):
		"""Verify hooks.py configuration for Haven app icon and website routing."""
		# Check add_to_apps_screen has Haven
		self.assertTrue(any(
			app.get("name") in ("heaven", "haven") and app.get("route") == "/heaven/app/"
			for app in hooks.add_to_apps_screen
		))

		# Check website_route_rules routes /heaven/<path:app_path> to heaven
		self.assertTrue(any(
			rule.get("from_route") == "/heaven/<path:app_path>" and rule.get("to_route") == "heaven"
			for rule in hooks.website_route_rules
		))

		# Check app_include_js includes heaven_desk.js
		self.assertTrue(any(
			"heaven_desk.js" in script
			for script in hooks.app_include_js
		))

	def test_sso_token_generation_hr_roles(self):
		"""Verify that HR users and administrators can generate signed SSO exchange tokens."""
		import jwt
		from hrms.api.haven_auth import generate_sso_exchange_token, get_mapped_haven_role

		mock_frappe = MagicMock()
		mock_frappe.conf.get.return_value = "test_secret"

		# Administrator -> HR_ADMIN
		mock_frappe.session.user = "Administrator"
		with patch("hrms.api.haven_auth.frappe", mock_frappe):
			self.assertEqual(get_mapped_haven_role("Administrator"), "HR_ADMIN")
			token = generate_sso_exchange_token("Administrator")
			decoded = jwt.decode(token, "test_secret", algorithms=["HS256"], audience="haven", issuer="hrms")
			self.assertEqual(decoded["sub"], "Administrator")
			self.assertEqual(decoded["role"], "HR_ADMIN")
			self.assertEqual(decoded["type"], "sso_exchange")
			self.assertIn("jti", decoded)

		# HR User -> MANAGER
		mock_frappe.session.user = "hr_user@company.com"
		mock_frappe.get_roles.return_value = ["HR User", "Employee"]
		with patch("hrms.api.haven_auth.frappe", mock_frappe):
			self.assertEqual(get_mapped_haven_role("hr_user@company.com"), "MANAGER")
			token = generate_sso_exchange_token("hr_user@company.com")
			decoded = jwt.decode(token, "test_secret", algorithms=["HS256"], audience="haven", issuer="hrms")
			self.assertEqual(decoded["sub"], "hr_user@company.com")
			self.assertEqual(decoded["role"], "MANAGER")

	def test_sso_token_generation_unauthorized_employee(self):
		"""Verify that non-HR employees are blocked from generating SSO exchange tokens."""
		from hrms.api.haven_auth import generate_sso_exchange_token, get_mapped_haven_role

		mock_frappe = MagicMock()
		mock_frappe.session.user = "regular_dev@company.com"
		mock_frappe.get_roles.return_value = ["Employee"]
		mock_frappe.PermissionError = Exception
		mock_frappe.throw.side_effect = Exception("Unauthorized")

		with patch("hrms.api.haven_auth.frappe", mock_frappe):
			self.assertIsNone(get_mapped_haven_role("regular_dev@company.com"))
			with self.assertRaises(Exception):
				generate_sso_exchange_token("regular_dev@company.com")


if __name__ == "__main__":
	unittest.main()
