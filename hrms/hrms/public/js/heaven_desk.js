/**
 * heaven_desk.js
 * - Hides ERPNext from the Frappe Desk apps screen (UI only; backend is untouched).
 * - Manages Haven app icon beside HRMS on desktop homepage:
 *     * Visible ONLY to users with approved HR roles.
 *     * Hidden completely for employees and non-HR users.
 *     * Directs to /heaven/app/.
 * - Runs once the desk is ready and also watches for dynamic re-renders.
 */
frappe.ready(function () {
	hideErpNextFromDesk();
	cleanSidebarItems();
	manageHavenAppIcon();

	// Watch for dynamic DOM changes (Frappe re-renders the apps section and dock on navigation)
	if (typeof MutationObserver !== "undefined") {
		const observer = new MutationObserver(function () {
			hideErpNextFromDesk();
			cleanSidebarItems();
			manageHavenAppIcon();
		});
		observer.observe(document.body, { childList: true, subtree: true });
	}
});

function isUserHrRole() {
	if (typeof frappe === "undefined") return false;
	if (frappe.session && frappe.session.user === "Administrator") return true;

	if (frappe.boot && frappe.boot.has_haven_permission !== undefined) {
		return Boolean(frappe.boot.has_haven_permission);
	}

	const roles = frappe.user_roles || (frappe.boot && frappe.boot.user && frappe.boot.user.roles) || [];
	const hrRoles = ["HR Manager", "HR User", "System Manager"];
	return roles.some(function (r) {
		return hrRoles.indexOf(r) !== -1;
	});
}

function manageHavenAppIcon() {
	const isHr = isUserHrRole();

	const havenSelectors = [
		'[data-app-name="heaven"]',
		'[data-app-name="haven"]',
		'.app-card[title="Haven"]',
		'.app-card[title="Heaven"]',
		'a[href*="/heaven"]',
		'.app-item[data-route*="heaven"]',
		'.app-item[data-route*="haven"]',
	];

	if (!isHr) {
		// Employees and non-HR users must NOT see the Haven icon
		havenSelectors.forEach(function (sel) {
			document.querySelectorAll(sel).forEach(function (el) {
				el.style.setProperty("display", "none", "important");
			});
		});
		return;
	}

	// For HR users: ensure visible, branded as "Haven", and routes to "/heaven/app/"
	havenSelectors.forEach(function (sel) {
		document.querySelectorAll(sel).forEach(function (el) {
			el.style.removeProperty("display");

			if (el.tagName === "A" && el.getAttribute("href") && el.getAttribute("href").indexOf("/heaven") !== -1) {
				el.setAttribute("href", "/heaven/app/");
			}
			const anchor = el.querySelector("a") || (el.tagName === "A" ? el : el.closest("a"));
			if (anchor && anchor.getAttribute("href") && anchor.getAttribute("href").indexOf("/heaven") !== -1) {
				anchor.setAttribute("href", "/heaven/app/");
			}

			const titleEl = el.querySelector(".app-title, .title, span, p");
			if (titleEl && titleEl.textContent && titleEl.textContent.trim().toLowerCase() === "heaven") {
				titleEl.textContent = "Haven";
			}
			if (el.getAttribute("title") && el.getAttribute("title").toLowerCase() === "heaven") {
				el.setAttribute("title", "Haven");
			}
		});
	});
}

function cleanSidebarItems() {
	const dock = document.querySelector(".dock") || document.querySelector('[aria-label="Workspaces"]');
	if (!dock) return;

	const toHide = [
		"search",
		"notifications",
		"recruitment",
		"expenses",
		"tax & benefits",
		"tax &amp; benefits",
	];

	dock.querySelectorAll("button, .dock-item, .dock-shortcuts button").forEach(function (el) {
		const label = (
			el.getAttribute("aria-label") ||
			el.textContent ||
			el.getAttribute("title") ||
			""
		)
			.trim()
			.toLowerCase();
		if (
			toHide.some(function (h) {
				return label === h || label.indexOf(h) !== -1;
			})
		) {
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
