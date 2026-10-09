import frappe


def patch_app_data(bootinfo):
	"""
	Post-process bootinfo.app_data to:
	  1. Hide ERPNext from the apps screen (backend stays fully intact)
	  2. Inject an 'HR' tile (sequence_id=2) so it shows between Heaven and Framework
	"""
	if not hasattr(bootinfo, "app_data") or not bootinfo.app_data:
		return

	# ── 1. Hide ERPNext and Framework from the apps screen ───────────────────────
	for app in bootinfo.app_data:
		if app.get("app_name") in ("erpnext", "frappe"):
			app["on_apps_screen"] = False

	# ── 2. Build the HR tile ────────────────────────────────────────────────────
	# Check permission the same way the original hrms hook did
	hr_visible = True
	try:
		from hrms.hr.utils import check_app_permission
		if not check_app_permission():
			hr_visible = False
	except Exception:
		pass  # If the check fails, default to showing the tile

	hr_entry = {
		"on_apps_screen": hr_visible,
		"sequence_id": 2,
		"app_name": "hrms",
		"app_title": "HR",
		"app_route": "/desk/hr-setup",  # Opens Frappe desk HRMS — no re-login needed
		"desk_route": "",               # Empty = no "Open in Desk" secondary link
		"app_logo_url": "/assets/hrms/images/frappe-hr-logo.svg",
		"dock": [],
	}

	bootinfo.app_data.append(hr_entry)

	# ── 3. Filter Dock / Sidebar items (UI only) ───────────────────────────────
	# Hide Recruitment, Expenses, Tax & Benefits from the left sidebar
	hidden_items = {"recruitment", "expenses", "tax & benefits"}

	if hasattr(bootinfo, "dock") and bootinfo.dock:
		for app_key, dock_items in bootinfo.dock.items():
			if isinstance(dock_items, list):
				bootinfo.dock[app_key] = [
					item for item in dock_items
					if (item.get("title") or "").strip().lower() not in hidden_items
					and (item.get("link_to") or "").strip().lower() not in hidden_items
				]

	for app in bootinfo.app_data:
		if "dock" in app and isinstance(app.get("dock"), list):
			app["dock"] = [
				item for item in app["dock"]
				if (item.get("title") or "").strip().lower() not in hidden_items
				and (item.get("link_to") or "").strip().lower() not in hidden_items
			]

