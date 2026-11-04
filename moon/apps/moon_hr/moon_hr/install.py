# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DEFAULT_POLICIES = [
	# name, employment type, hours/day, working days (Mon..Sun), start, half-day threshold, auto break, description
	(
		"Full-time (40 h/week)",
		"Full-time",
		8,
		"1111100",
		"10:00:00",
		4,
		0,
		"Standard 8 hours a day, Monday to Friday. Lunch is taken by clocking out.",
	),
	(
		"Part-time / Half-time (20 h/week)",
		"Part-time",
		4,
		"1111100",
		"10:00:00",
		2,
		0,
		"Half-time role: 4 hours a day, Monday to Friday.",
	),
	(
		"Intern (30 h/week)",
		"Intern",
		6,
		"1111100",
		"10:30:00",
		3,
		30,
		"Interns work 6 hours a day; a 30 minute break is auto-deducted on single long sessions.",
	),
	(
		"Contract (45 h/week)",
		"Contract",
		9,
		"1111100",
		"09:30:00",
		4.5,
		0,
		"Contractors billed on 9 hour days.",
	),
	(
		"Probation (40 h/week)",
		"Probation",
		8,
		"1111100",
		"10:00:00",
		4,
		0,
		"Same as full-time during probation.",
	),
	(
		"Apprentice (36 h/week)",
		"Apprentice",
		6,
		"1111110",
		"10:00:00",
		3,
		0,
		"Apprentices: 6 hours, Monday to Saturday.",
	),
	(
		"24x7 Ops - 6 day week (48 h/week)",
		None,
		8,
		"1111110",
		"06:00:00",
		4,
		0,
		"Exchange operations / support desk on rotating shifts, 6 days a week. Assign per person.",
	),
]


def after_install():
	create_roles()
	create_employee_fields()
	create_default_policies()
	create_kanban_boards()
	frappe.db.commit()


def after_migrate():
	create_roles()
	create_employee_fields()
	create_kanban_boards()


def create_roles():
	for role, desk in (("CRM User", 1),):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk}).insert(
				ignore_permissions=True
			)


def create_employee_fields():
	meta = frappe.get_meta("Employee")
	last = meta.fields[-1].fieldname if meta.fields else None
	if meta.has_field("moon_work_hours_tab"):
		last = None  # already placed
	fields = [
		dict(fieldname="moon_work_hours_tab", label="Work Hours", fieldtype="Tab Break", insert_after=last),
		dict(
			fieldname="moon_work_hour_policy",
			label="Personal Work Hour Policy",
			fieldtype="Link",
			options="Work Hour Policy",
			insert_after="moon_work_hours_tab",
			description="Leave empty to use the policy of the employee's Employment Type.",
		),
		dict(
			fieldname="moon_daily_hours_override",
			label="Personal Hours per Day",
			fieldtype="Float",
			insert_after="moon_work_hour_policy",
			description="Person-specific target, e.g. 6 for a reduced schedule. Overrides the policy.",
		),
		dict(
			fieldname="moon_effective_daily_hours",
			label="Effective Hours per Day",
			fieldtype="Float",
			read_only=1,
			insert_after="moon_daily_hours_override",
		),
		dict(fieldname="moon_wh_cb", fieldtype="Column Break", insert_after="moon_effective_daily_hours"),
		dict(
			fieldname="moon_hours_this_week",
			label="Worked This Week (h)",
			fieldtype="Float",
			read_only=1,
			insert_after="moon_wh_cb",
		),
		dict(
			fieldname="moon_expected_this_week",
			label="Expected This Week (h)",
			fieldtype="Float",
			read_only=1,
			insert_after="moon_hours_this_week",
		),
		dict(
			fieldname="moon_hours_this_month",
			label="Worked This Month (h)",
			fieldtype="Float",
			read_only=1,
			insert_after="moon_expected_this_week",
		),
		dict(
			fieldname="moon_expected_this_month",
			label="Expected This Month (h)",
			fieldtype="Float",
			read_only=1,
			insert_after="moon_hours_this_month",
		),
		dict(
			fieldname="moon_overtime_this_month",
			label="Overtime This Month (h)",
			fieldtype="Float",
			read_only=1,
			insert_after="moon_expected_this_month",
		),
	]
	if not last:
		fields[0].pop("insert_after")
	create_custom_fields({"Employee": fields}, ignore_validate=True, update=True)


def create_default_policies():
	for name, emp_type, hours, days, start, half, brk, desc in DEFAULT_POLICIES:
		if frappe.db.exists("Work Hour Policy", name):
			continue
		if emp_type and not frappe.db.exists("Employment Type", emp_type):
			frappe.get_doc({"doctype": "Employment Type", "employee_type_name": emp_type}).insert(
				ignore_permissions=True
			)
		doc = frappe.new_doc("Work Hour Policy")
		doc.update(
			{
				"policy_name": name,
				"employment_type": emp_type,
				"daily_hours": hours,
				"start_time": start,
				"half_day_threshold": half,
				"auto_break_minutes": brk,
				"description": desc,
				"is_default": 1 if emp_type == "Full-time" else 0,
			}
		)
		for flag, day in zip(
			days, ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], strict=False
		):
			doc.set(day, int(flag))
		doc.insert(ignore_permissions=True)


def create_kanban_boards():
	boards = [
		(
			"Opportunities by Stage",
			"Pipeline Opportunity",
			"stage",
			["New", "Screening", "Meeting", "Proposal", "Customer", "Lost"],
			["Gray", "Blue", "Purple", "Orange", "Green", "Red"],
		),
		(
			"Tasks by Status",
			"Pipeline Task",
			"status",
			["To do", "In progress", "Done"],
			["Gray", "Orange", "Green"],
		),
	]
	for name, doctype, field, columns, colors in boards:
		if frappe.db.exists("Kanban Board", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Kanban Board",
				"kanban_board_name": name,
				"reference_doctype": doctype,
				"field_name": field,
				"private": 0,
				"show_labels": 1,
				"columns": [
					{"column_name": c, "status": "Active", "indicator": col}
					for c, col in zip(columns, colors, strict=False)
				],
			}
		).insert(ignore_permissions=True)
