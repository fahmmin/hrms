import frappe


def has_app_permission():
	roles = set(frappe.get_roles())
	return bool(roles & {"System Manager", "HR Manager", "HR User", "CRM User", "Sales Manager"})
