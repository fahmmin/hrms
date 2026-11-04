# Copyright (c) 2026, Moon Exchange
"""Non-interactive setup wizard: creates the Moon Exchange company, fiscal year and defaults."""

import frappe
from frappe.utils import getdate, nowdate

COMPANY = "Moon Exchange"
ABBR = "MX"


def fiscal_year_dates(today=None):
	"""Indian fiscal year (1 April - 31 March) containing `today`."""
	today = getdate(today or nowdate())
	start_year = today.year if today.month >= 4 else today.year - 1
	return f"{start_year}-04-01", f"{start_year + 1}-03-31"


def complete_setup():
	if frappe.is_setup_complete() and frappe.db.exists("Company", COMPANY):
		print("Setup already complete")
		return

	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	fy_start, fy_end = fiscal_year_dates()
	args = {
		"language": "English",
		"country": "India",
		"timezone": "Asia/Kolkata",
		"time_zone": "Asia/Kolkata",
		"currency": "INR",
		"full_name": "Moon HR Admin",
		"email": "hr.admin@demo.moon.exchange",
		"password": frappe.conf.get("admin_password") or "admin",
		"company_name": COMPANY,
		"company_abbr": ABBR,
		"company_tagline": "FIU-IND registered crypto exchange",
		"chart_of_accounts": "Standard",
		"fy_start_date": fy_start,
		"fy_end_date": fy_end,
		"setup_demo": 0,
		"enable_telemetry": 0,
	}
	frappe.set_user("Administrator")
	result = setup_complete(args)
	frappe.db.commit()
	print("Setup wizard:", result)

	# Sensible system defaults for an Indian company
	ss = frappe.get_single("System Settings")
	ss.update(
		{
			"time_zone": "Asia/Kolkata",
			"country": "India",
			"currency": "INR",
			"date_format": "dd-mm-yyyy",
			"number_format": "#,##,###.##",
			"float_precision": "2",
		}
	)
	ss.flags.ignore_mandatory = True
	ss.save(ignore_permissions=True)
	frappe.db.commit()
