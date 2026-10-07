import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

field_name = "custom_github_username"

if not frappe.db.exists("Custom Field", f"Employee-{field_name}"):
    create_custom_field("Employee", {
        "fieldname": field_name,
        "label": "GitHub Username",
        "fieldtype": "Data",
        "insert_after": "user_id",
        "description": "Used to map employee activity to GitHub commits for the ML Data Aggregator."
    })
    frappe.db.commit()
    print("Success: 'GitHub Username' field added to Employee.")
else:
    print("Field 'custom_github_username' already exists.")
