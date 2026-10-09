/**
 * heaven_desk.js
 * Hides ERPNext from the Frappe Desk apps screen (UI only; backend is untouched).
 * Runs once the desk is ready and also watches for dynamic re-renders.
 */
frappe.ready(function () {
	hideErpNextFromDesk();
	cleanSidebarItems();

	// Watch for dynamic DOM changes (Frappe re-renders the apps section and dock on navigation)
	if (typeof MutationObserver !== "undefined") {
		const observer = new MutationObserver(function () {
			hideErpNextFromDesk();
			cleanSidebarItems();
		});
		observer.observe(document.body, { childList: true, subtree: true });
	}
});

function cleanSidebarItems() {
	const dock = document.querySelector(".dock") || document.querySelector('[aria-label="Workspaces"]');
	if (!dock) return;

	const toHide = [
		"search",
		"notifications",
		"recruitment",
		"expenses",
		"tax & benefits",
		"tax &amp; benefits"
	];

	dock.querySelectorAll("button, .dock-item, .dock-shortcuts button").forEach(function (el) {
		const label = (el.getAttribute("aria-label") || el.textContent || el.getAttribute("title") || "").trim().toLowerCase();
		if (toHide.some(function (h) { return label === h || label.indexOf(h) !== -1; })) {
			el.style.setProperty("display", "none", "important");
		}
	});
}

function hideErpNextFromDesk() {
	// Frappe's desk app items – selectors for erpnext and framework/frappe
	const selectors = [
		'[data-app-name="erpnext"]',
		'.app-card[title="ERPNext"]',
		'.app-item[data-route*="erpnext"]',
		'[data-app-name="frappe"]',
		'.app-card[title="Framework"]',
		'a[href="/app/build"]',
	];

	selectors.forEach(function (sel) {
		document.querySelectorAll(sel).forEach(function (el) {
			el.style.setProperty("display", "none", "important");
		});
	});

	// Text-based fallback: hide any .app-item whose label is "ERPNext" or "Framework"
	document.querySelectorAll(".app-item, .app-card, .desk-app").forEach(function (el) {
		const label =
			el.querySelector(".app-title, .title, span, p")?.textContent?.trim() ||
			el.getAttribute("title") ||
			"";
		if (label === "ERPNext" || label === "Framework") {
			el.style.setProperty("display", "none", "important");
		}
	});
}

