# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt
"""Expected vs worked hours per person, using each person's own work-hour policy."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.from_date = getdate(filters.from_date or add_days(nowdate(), -30))
	filters.to_date = getdate(filters.to_date or nowdate())
	if filters.view == "Daily":
		return daily(filters)
	return summary(filters)


def get_conditions(filters):
	cond, values = ["wl.date between %(from_date)s and %(to_date)s"], dict(filters)
	for key in ("employee", "company", "department", "employment_type"):
		if filters.get(key):
			cond.append(f"wl.{key} = %({key})s")
	return " and ".join(cond), values


def summary(filters):
	cond, values = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select wl.employee, wl.employee_name, wl.department, wl.employment_type,
			max(wl.work_hour_policy) as policy,
			sum(wl.day_type in ('Working Day', 'Half Day Leave')) as working_days,
			sum(wl.worked_hours > 0) as days_worked,
			sum(wl.day_type in ('On Leave', 'Half Day Leave')) as leave_days,
			sum(wl.status = 'Absent') as absent_days,
			sum(wl.late_by_minutes > 0) as late_days,
			sum(wl.expected_hours) as expected_hours,
			sum(wl.worked_hours) as worked_hours,
			sum(wl.overtime_hours) as overtime_hours,
			sum(wl.shortfall_hours) as shortfall_hours
		from `tabEmployee Work Log` wl
		where {cond}
		group by wl.employee, wl.employee_name, wl.department, wl.employment_type
		order by wl.department, wl.employee_name
	""",
		values,
		as_dict=True,
	)

	daily_targets = {}
	if rows:
		from moon_hr.moon_hr.work_hours import get_employee_policy

		for r in rows:
			daily_targets[r.employee] = flt(get_employee_policy(r.employee).daily_hours)

	for r in rows:
		r.daily_target = daily_targets.get(r.employee)
		r.utilisation = (
			round(100 * flt(r.worked_hours) / flt(r.expected_hours), 1) if flt(r.expected_hours) else None
		)
		r.avg_per_day = round(flt(r.worked_hours) / r.days_worked, 2) if r.days_worked else 0

	columns = [
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{"label": _("Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 160},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"label": _("Employment Type"),
			"fieldname": "employment_type",
			"fieldtype": "Link",
			"options": "Employment Type",
			"width": 110,
		},
		{
			"label": _("Policy"),
			"fieldname": "policy",
			"fieldtype": "Link",
			"options": "Work Hour Policy",
			"width": 170,
		},
		{"label": _("Target h/day"), "fieldname": "daily_target", "fieldtype": "Float", "width": 90},
		{"label": _("Working Days"), "fieldname": "working_days", "fieldtype": "Int", "width": 90},
		{"label": _("Days Worked"), "fieldname": "days_worked", "fieldtype": "Int", "width": 90},
		{"label": _("Leave Days"), "fieldname": "leave_days", "fieldtype": "Int", "width": 80},
		{"label": _("Absent"), "fieldname": "absent_days", "fieldtype": "Int", "width": 70},
		{"label": _("Late Days"), "fieldname": "late_days", "fieldtype": "Int", "width": 75},
		{"label": _("Expected h"), "fieldname": "expected_hours", "fieldtype": "Float", "width": 95},
		{"label": _("Worked h"), "fieldname": "worked_hours", "fieldtype": "Float", "width": 95},
		{"label": _("Overtime h"), "fieldname": "overtime_hours", "fieldtype": "Float", "width": 95},
		{"label": _("Shortfall h"), "fieldname": "shortfall_hours", "fieldtype": "Float", "width": 95},
		{"label": _("Utilisation %"), "fieldname": "utilisation", "fieldtype": "Percent", "width": 105},
		{"label": _("Avg h / day"), "fieldname": "avg_per_day", "fieldtype": "Float", "width": 90},
	]

	top = sorted(rows, key=lambda r: flt(r.worked_hours), reverse=True)[:20]
	chart = {
		"data": {
			"labels": [r.employee_name for r in top],
			"datasets": [
				{"name": _("Expected"), "values": [round(flt(r.expected_hours), 1) for r in top]},
				{"name": _("Worked"), "values": [round(flt(r.worked_hours), 1) for r in top]},
			],
		},
		"type": "bar",
		"colors": ["#c9d1dc", "#2490ef"],
		"barOptions": {"spaceRatio": 0.4},
	}

	total_exp = sum(flt(r.expected_hours) for r in rows)
	total_work = sum(flt(r.worked_hours) for r in rows)
	report_summary = [
		{"value": round(total_work, 1), "label": _("Hours Worked"), "datatype": "Float", "indicator": "Blue"},
		{"value": round(total_exp, 1), "label": _("Hours Expected"), "datatype": "Float"},
		{
			"value": round(100 * total_work / total_exp, 1) if total_exp else 0,
			"label": _("Utilisation %"),
			"datatype": "Percent",
			"indicator": "Green" if total_work >= total_exp * 0.95 else "Orange",
		},
		{
			"value": round(sum(flt(r.overtime_hours) for r in rows), 1),
			"label": _("Overtime Hours"),
			"datatype": "Float",
			"indicator": "Purple",
		},
		{
			"value": sum(int(r.late_days or 0) for r in rows),
			"label": _("Late Arrivals"),
			"datatype": "Int",
			"indicator": "Red",
		},
	]
	return columns, rows, None, chart, report_summary


def daily(filters):
	cond, values = get_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select wl.name as work_log, wl.date, wl.employee, wl.employee_name, wl.employment_type, wl.day_type, wl.status,
			wl.first_in, wl.last_out, wl.expected_hours, wl.worked_hours, wl.break_hours,
			wl.overtime_hours, wl.shortfall_hours, wl.late_by_minutes, wl.source
		from `tabEmployee Work Log` wl where {cond}
		order by wl.date desc, wl.employee_name
	""",
		values,
		as_dict=True,
	)
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Employee"),
			"fieldname": "employee",
			"fieldtype": "Link",
			"options": "Employee",
			"width": 115,
		},
		{"label": _("Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{"label": _("Type"), "fieldname": "employment_type", "fieldtype": "Data", "width": 90},
		{"label": _("Day"), "fieldname": "day_type", "fieldtype": "Data", "width": 100},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 95},
		{"label": _("First In"), "fieldname": "first_in", "fieldtype": "Datetime", "width": 150},
		{"label": _("Last Out"), "fieldname": "last_out", "fieldtype": "Datetime", "width": 150},
		{"label": _("Expected"), "fieldname": "expected_hours", "fieldtype": "Float", "width": 80},
		{"label": _("Worked"), "fieldname": "worked_hours", "fieldtype": "Float", "width": 80},
		{"label": _("Break"), "fieldname": "break_hours", "fieldtype": "Float", "width": 70},
		{"label": _("Overtime"), "fieldname": "overtime_hours", "fieldtype": "Float", "width": 80},
		{"label": _("Shortfall"), "fieldname": "shortfall_hours", "fieldtype": "Float", "width": 80},
		{"label": _("Late (min)"), "fieldname": "late_by_minutes", "fieldtype": "Int", "width": 80},
		{"label": _("Source"), "fieldname": "source", "fieldtype": "Data", "width": 85},
		{
			"label": _("Work Log"),
			"fieldname": "work_log",
			"fieldtype": "Link",
			"options": "Employee Work Log",
			"width": 200,
		},
	]
	by_day = {}
	for r in rows:
		d = by_day.setdefault(r.date, [0.0, 0.0])
		d[0] += flt(r.expected_hours)
		d[1] += flt(r.worked_hours)
	days = sorted(by_day)
	chart = {
		"data": {
			"labels": [str(d) for d in days],
			"datasets": [
				{"name": _("Expected"), "values": [round(by_day[d][0], 1) for d in days]},
				{"name": _("Worked"), "values": [round(by_day[d][1], 1) for d in days]},
			],
		},
		"type": "line",
		"colors": ["#c9d1dc", "#2490ef"],
	}
	return columns, rows, None, chart
