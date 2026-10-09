import frappe

def execute():
    frappe.db.sql("DELETE FROM `tabGender` WHERE name NOT IN ('Male', 'Female')")
    frappe.db.commit()
