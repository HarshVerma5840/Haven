import frappe

HR_APPROVED_ROLES = {"HR Manager", "HR User", "System Manager"}


def is_hr_user(user: str | None = None) -> bool:
	"""Check if user has approved HR roles.

	Only users with 'HR Manager', 'HR User', 'System Manager', or 'Administrator'
	can access Haven. Standard employees and non-HR users return False.
	"""
	if not user:
		user = frappe.session.user
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))
	return bool(HR_APPROVED_ROLES.intersection(user_roles))


def patch_app_data(bootinfo):
	"""Post-process bootinfo.app_data to:

	1. Hide ERPNext and Framework from the apps screen (backend stays fully intact)
	2. Inject the 'HR' tile (sequence_id=1)
	3. Configure the 'Haven' tile (sequence_id=2) beside HRMS, visible ONLY to HR roles.
	"""
	if not hasattr(bootinfo, "app_data") or not bootinfo.app_data:
		return

	# ── 1. Hide ERPNext and Framework from the apps screen ───────────────────────
	for app in bootinfo.app_data:
		if app.get("app_name") in ("erpnext", "frappe"):
			app["on_apps_screen"] = False

	# ── 2. Configure Haven Tile with Strict HR-Only Access ───────────────────────
	haven_allowed = is_hr_user()
	bootinfo.has_haven_permission = haven_allowed

	found_haven = False
	for app in bootinfo.app_data:
		if app.get("app_name") in ("heaven", "haven") or app.get("name") in ("heaven", "haven"):
			found_haven = True
			app["on_apps_screen"] = haven_allowed
			app["app_title"] = "Haven"
			app["title"] = "Haven"
			app["app_route"] = "/heaven/app/"
			app["route"] = "/heaven/app/"
			app["app_logo_url"] = "/assets/hrms/images/heaven-logo.svg"
			app["logo"] = "/assets/hrms/images/heaven-logo.svg"
			app["sequence_id"] = 2

	if not found_haven and haven_allowed:
		bootinfo.app_data.append(
			{
				"on_apps_screen": True,
				"sequence_id": 2,
				"name": "heaven",
				"app_name": "heaven",
				"title": "Haven",
				"app_title": "Haven",
				"route": "/heaven/app/",
				"app_route": "/heaven/app/",
				"logo": "/assets/hrms/images/heaven-logo.svg",
				"app_logo_url": "/assets/hrms/images/heaven-logo.svg",
				"dock": [],
			}
		)

	# ── 3. Build the HR Tile ─────────────────────────────────────────────────────
	hr_visible = True
	try:
		from hrms.hr.utils import check_app_permission

		if not check_app_permission():
			hr_visible = False
	except Exception:
		pass  # If the check fails, default to showing the tile

	hr_entry = {
		"on_apps_screen": hr_visible,
		"sequence_id": 1,
		"app_name": "hrms",
		"app_title": "HR",
		"app_route": "/desk/hr-setup",  # Opens Frappe desk HRMS — no re-login needed
		"desk_route": "",  # Empty = no "Open in Desk" secondary link
		"app_logo_url": "/assets/hrms/images/frappe-hr-logo.svg",
		"dock": [],
	}

	bootinfo.app_data.append(hr_entry)

	# ── 4. Filter Dock / Sidebar items (UI only) ────────────────────────────────
	hidden_items = {"recruitment", "expenses", "tax & benefits"}

	if hasattr(bootinfo, "dock") and bootinfo.dock:
		for app_key, dock_items in bootinfo.dock.items():
			if isinstance(dock_items, list):
				bootinfo.dock[app_key] = [
					item
					for item in dock_items
					if (item.get("title") or "").strip().lower() not in hidden_items
					and (item.get("link_to") or "").strip().lower() not in hidden_items
				]

	for app in bootinfo.app_data:
		if "dock" in app and isinstance(app.get("dock"), list):
			app["dock"] = [
				item
				for item in app["dock"]
				if (item.get("title") or "").strip().lower() not in hidden_items
				and (item.get("link_to") or "").strip().lower() not in hidden_items
			]
