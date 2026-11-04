app_name = "moon_hr"
app_title = "Moon HR"
app_publisher = "Moon Exchange"
app_description = "Moon Exchange extensions for Frappe HR: work hours, CRM, About page and demo data"
app_email = "hr@moon.exchange"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext", "frappe/hrms"]

# Installation
# ------------
after_install = "moon_hr.install.after_install"
after_migrate = "moon_hr.install.after_migrate"

# Document events
# ---------------
doc_events = {
	"Employee Checkin": {
		"after_insert": "moon_hr.moon_hr.work_hours.on_checkin_change",
		"on_update": "moon_hr.moon_hr.work_hours.on_checkin_change",
		"on_trash": "moon_hr.moon_hr.work_hours.on_checkin_change",
	},
}

# Scheduled tasks
# ---------------
scheduler_events = {
	"hourly": [
		"moon_hr.moon_hr.work_hours.refresh_today",
	],
	"daily": [
		"moon_hr.moon_hr.work_hours.refresh_recent_days",
	],
}

# Website
# -------
website_route_rules = [
	{"from_route": "/team", "to_route": "about"},
]

# Desk UI
# -------
doctype_js = {"Employee": "public/js/employee_work_hours.js"}

add_to_apps_screen = [
	{
		"name": "moon_hr",
		"logo": "/assets/moon_hr/icons/moon.svg",
		"title": "Moon Exchange",
		"route": "/desk/moon-exchange",
		"has_permission": "moon_hr.utils.has_app_permission",
	},
]
