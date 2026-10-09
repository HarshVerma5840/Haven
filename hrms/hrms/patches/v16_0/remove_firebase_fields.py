import frappe

def execute():
    fields_to_remove = [
        "firebase_uid", 
        "firebase_provisioning_section", 
        "firebase_provisioning_status", 
        "firebase_invitation_status", 
        "firebase_last_provisioned_on", 
        "firebase_provisioning_message"
    ]
    
    # Remove custom fields from metadata
    frappe.db.delete("Custom Field", {"fieldname": ("in", fields_to_remove)})
    
    # Drop columns from database safely
    if frappe.db.has_column("User", "firebase_uid"):
        frappe.db.sql("ALTER TABLE `tabUser` DROP COLUMN `firebase_uid`")
        
    for field in fields_to_remove:
        if field != "firebase_uid" and frappe.db.has_column("Employee", field):
            frappe.db.sql(f"ALTER TABLE `tabEmployee` DROP COLUMN `{field}`")
            
    frappe.clear_cache(doctype="User")
    frappe.clear_cache(doctype="Employee")
