# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt
"""Person-specific work hours.

Every employee gets an *expected* number of hours per day which is resolved in this order:

1. ``Employee.moon_daily_hours_override``  (person-specific number, e.g. a 6 h/day reduced schedule)
2. ``Employee.moon_work_hour_policy``      (personal policy, e.g. "Support - 6 day week")
3. the Work Hour Policy linked to the employee's Employment Type (Full-time / Part-time / Intern ...)
4. the default Work Hour Policy
5. a built-in fallback of 8 h, Monday-Friday

*Worked* hours come from Employee Checkin (clock-in / clock-out from the mobile app, web or a
biometric device). Check-ins are paired into sessions, so breaks taken by clocking out are not
counted. When an employee has no check-ins, the Attendance record's working hours are used instead
(e.g. attendance marked from a biometric summary or Work From Home).

The result is stored per employee per day in **Employee Work Log** and rolled up on the Employee
record (hours this week / this month / overtime this month).
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, cint, flt, get_datetime, getdate, now_datetime, nowdate

DAY_FIELDS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
TOLERANCE_HOURS = 0.25  # up to 15 minutes short still counts as "On Track"
OVERTIME_MIN_HOURS = 0.5  # overtime starts after 30 minutes beyond the daily target
LONG_SESSION_HOURS = 5

FALLBACK_POLICY = frappe._dict(
	name=None,
	daily_hours=8.0,
	start_time="10:00:00",
	grace_minutes=15,
	auto_break_minutes=0,
	half_day_threshold=4.0,
	overtime_after=8.0,
	count_off_day_as_overtime=1,
	**{d: 1 if i < 5 else 0 for i, d in enumerate(DAY_FIELDS)},
)


# --------------------------------------------------------------------------- policy resolution
def get_employee_policy(employee: str | dict) -> frappe._dict:
	"""Return the effective work-hour policy for an employee, with person overrides applied."""
	emp = employee if isinstance(employee, dict) else get_employee_row(employee)
	policy_name = emp.get("moon_work_hour_policy")
	if not policy_name and emp.get("employment_type"):
		policy_name = frappe.db.get_value(
			"Work Hour Policy", {"employment_type": emp.employment_type}, "name"
		)
	if not policy_name:
		policy_name = frappe.db.get_value("Work Hour Policy", {"is_default": 1}, "name")

	policy = frappe._dict(FALLBACK_POLICY)
	if policy_name:
		policy.update(frappe.get_cached_doc("Work Hour Policy", policy_name).as_dict())
		policy.name = policy_name

	if flt(emp.get("moon_daily_hours_override")):
		policy.daily_hours = flt(emp.moon_daily_hours_override)
		policy.overtime_after = 0  # follow the personal target

	policy.overtime_after = flt(policy.overtime_after) or flt(policy.daily_hours)
	return policy


def get_employee_row(employee: str) -> frappe._dict:
	fields = [
		"name",
		"employee_name",
		"company",
		"employment_type",
		"department",
		"default_shift",
		"date_of_joining",
		"relieving_date",
		"status",
	]
	for f in ("moon_work_hour_policy", "moon_daily_hours_override"):
		if frappe.get_meta("Employee").has_field(f):
			fields.append(f)
	return frappe.db.get_value("Employee", employee, fields, as_dict=True)


def is_working_day(policy, date) -> bool:
	return bool(cint(policy.get(DAY_FIELDS[getdate(date).weekday()])))


# --------------------------------------------------------------------------- day calculation
def compute_day(
	employee: str | dict,
	date,
	holidays: set | None = None,
	leaves: dict | None = None,
	checkins: list | None = None,
) -> frappe._dict:
	"""Calculate the work log values for one employee and day (does not save)."""
	emp = employee if isinstance(employee, dict) else get_employee_row(employee)
	date = getdate(date)
	policy = get_employee_policy(emp)

	if holidays is None:
		holidays = get_holiday_set(emp.name, date, date)
	if leaves is None:
		leaves = get_leave_map(emp.name, date, date)
	if checkins is None:
		checkins = get_checkins(emp.name, date, date).get(date, [])

	# ---- expected hours for the day
	daily = flt(policy.daily_hours)
	if date in holidays:
		day_type, expected = "Holiday", 0.0
	elif not is_working_day(policy, date):
		day_type, expected = "Weekly Off", 0.0
	elif date in leaves:
		half = leaves[date]
		day_type, expected = ("Half Day Leave", daily / 2) if half else ("On Leave", 0.0)
	else:
		day_type, expected = "Working Day", daily

	# ---- worked hours from clock-ins
	sessions, open_session = pair_sessions(checkins, date)
	source = "Check-in" if checkins else "None"
	worked = sum(s["hours"] for s in sessions)
	in_progress = False
	if open_session and date == getdate(nowdate()):
		live = (now_datetime() - open_session).total_seconds() / 3600
		sessions.append(
			{"in_time": open_session, "out_time": None, "hours": round(live, 2), "note": "Clocked in"}
		)
		worked += live
		in_progress = True
	elif open_session:
		sessions.append({"in_time": open_session, "out_time": None, "hours": 0, "note": "Missing check-out"})

	if len(sessions) == 1 and worked > LONG_SESSION_HOURS and cint(policy.auto_break_minutes):
		worked -= cint(policy.auto_break_minutes) / 60

	if not checkins:
		att = frappe.db.get_value(
			"Attendance",
			{"employee": emp.name, "attendance_date": date, "docstatus": 1},
			["status", "working_hours"],
			as_dict=True,
		)
		if att and flt(att.working_hours):
			worked, source = flt(att.working_hours), "Attendance"
		elif att and att.status == "Work From Home":
			worked, source = expected, "Attendance"
		elif att and att.status == "Half Day" and day_type == "Working Day":
			worked, source = daily / 2, "Attendance"

	first_in = sessions[0]["in_time"] if sessions else None
	closed = [s for s in sessions if s["out_time"]]
	last_out = closed[-1]["out_time"] if closed else None
	span = ((last_out - first_in).total_seconds() / 3600) if first_in and last_out else 0
	break_hours = max(0.0, span - worked) if span else 0.0

	# ---- derived figures
	if day_type in ("Working Day", "Half Day Leave"):
		threshold = max(flt(policy.overtime_after), expected) if day_type == "Working Day" else expected
		overtime = worked - threshold
		overtime = overtime if overtime >= OVERTIME_MIN_HOURS else 0.0
	else:
		overtime = worked if cint(policy.count_off_day_as_overtime) else 0.0
	shortfall = max(0.0, expected - worked) if not in_progress else 0.0

	late = 0
	start = get_expected_start(emp, policy)
	if first_in and start and day_type == "Working Day":
		expected_start = datetime.combine(date, start) + timedelta(minutes=cint(policy.grace_minutes))
		if first_in > expected_start:
			late = int((first_in - expected_start).total_seconds() // 60)

	status = get_status(day_type, expected, worked, policy, in_progress, date)

	return frappe._dict(
		employee=emp.name,
		date=date,
		day_type=day_type,
		status=status,
		work_hour_policy=policy.name,
		source=source,
		expected_hours=round(expected, 2),
		worked_hours=round(worked, 2),
		break_hours=round(break_hours, 2),
		overtime_hours=round(overtime, 2),
		shortfall_hours=round(shortfall, 2),
		late_by_minutes=late,
		first_in=first_in,
		last_out=last_out,
		sessions=sessions,
	)


def get_status(day_type, expected, worked, policy, in_progress, date) -> str:
	if in_progress:
		return "In Progress"
	if day_type == "Holiday":
		return "Overtime" if worked and cint(policy.count_off_day_as_overtime) else "Holiday"
	if day_type == "Weekly Off":
		return "Overtime" if worked and cint(policy.count_off_day_as_overtime) else "Weekly Off"
	if day_type == "On Leave":
		return "On Leave"
	if getdate(date) >= getdate(nowdate()):
		# the day isn't over yet: don't judge it
		return "In Progress" if worked else ""
	if not worked:
		return "Absent"
	if day_type == "Working Day" and worked >= max(expected, flt(policy.overtime_after)) + OVERTIME_MIN_HOURS:
		return "Overtime"
	if worked >= expected - TOLERANCE_HOURS:
		return "On Track"
	if worked < flt(policy.half_day_threshold) and day_type == "Working Day":
		return "Half Day"
	return "Short"


def get_expected_start(emp, policy) -> time | None:
	start = None
	if emp.get("default_shift"):
		start = frappe.get_cached_value("Shift Type", emp.default_shift, "start_time")
	start = start or policy.get("start_time")
	if not start:
		return None
	if isinstance(start, timedelta):
		return (datetime.min + start).time()
	if isinstance(start, str):
		return datetime.strptime(start.split(".")[0], "%H:%M:%S").time()
	return start


def pair_sessions(checkins: list, date) -> tuple[list[dict], datetime | None]:
	"""Pair IN/OUT check-ins into sessions. Logs without a type alternate IN, OUT, IN, OUT..."""
	sessions, current = [], None
	expect_in = True
	for c in sorted(checkins, key=lambda c: get_datetime(c.time)):
		t = get_datetime(c.time)
		log_type = c.get("log_type") or ("IN" if expect_in else "OUT")
		if log_type == "IN":
			if current is None:
				current = t
			expect_in = False
		else:  # OUT
			if current is not None:
				hours = (t - current).total_seconds() / 3600
				sessions.append({"in_time": current, "out_time": t, "hours": round(hours, 2), "note": ""})
				current = None
			expect_in = True
	return sessions, current


# --------------------------------------------------------------------------- bulk data helpers
def get_holiday_set(employee: str, from_date, to_date) -> set:
	try:
		from hrms.hr.utils import get_holidays_for_employee

		rows = get_holidays_for_employee(
			employee, from_date, to_date, raise_exception=False, only_non_weekly=True
		)
		return {getdate(r.holiday_date) for r in rows}
	except Exception:
		return set()


def get_leave_map(employee: str, from_date, to_date) -> dict:
	"""{date: is_half_day} for approved leave applications."""
	out = {}
	apps = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		fields=["from_date", "to_date", "half_day", "half_day_date"],
	)
	for a in apps:
		d = getdate(a.from_date)
		while d <= getdate(a.to_date):
			if getdate(from_date) <= d <= getdate(to_date):
				out[d] = bool(
					a.half_day
					and (not a.half_day_date or getdate(a.half_day_date) == d or a.from_date == a.to_date)
				)
			d = add_days(d, 1)
	return out


def get_checkins(employee: str, from_date, to_date) -> dict:
	"""Check-ins grouped by the *logical* day (shift start date, so night shifts stay on one day)."""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [add_days(from_date, -1), add_to_date(getdate(to_date), days=1, hours=12)]],
		},
		fields=["name", "time", "log_type", "shift_start"],
		order_by="time asc",
	)
	out = {}
	for r in rows:
		day = getdate(r.shift_start) if r.shift_start else getdate(r.time)
		if getdate(from_date) <= day <= getdate(to_date):
			out.setdefault(day, []).append(r)
	return out


# --------------------------------------------------------------------------- persistence
def upsert_log(values: frappe._dict) -> str:
	name = frappe.db.get_value("Employee Work Log", {"employee": values.employee, "date": values.date})
	if name:
		doc = frappe.get_doc("Employee Work Log", name)
		if doc.is_manual:
			# keep the manually typed hours, refresh only the expectation side
			for key in ("day_type", "expected_hours", "work_hour_policy"):
				doc.set(key, values[key])
			doc.save(ignore_permissions=True)
			return doc.name
	else:
		doc = frappe.new_doc("Employee Work Log")
		doc.employee = values.employee
		doc.date = values.date

	sessions = values.pop("sessions", [])
	doc.update(values)
	doc.set("sessions", [])
	for s in sessions:
		doc.append("sessions", s)
	doc.flags.from_engine = True
	doc.save(ignore_permissions=True)
	return doc.name


def recalculate_employee(employee: str, from_date, to_date, update_summary: bool = True) -> int:
	emp = get_employee_row(employee)
	if not emp:
		return 0
	from_date, to_date = getdate(from_date), min(getdate(to_date), getdate(nowdate()))
	if emp.date_of_joining:
		from_date = max(from_date, getdate(emp.date_of_joining))
	if emp.relieving_date:
		to_date = min(to_date, getdate(emp.relieving_date))
	if from_date > to_date:
		return 0

	holidays = get_holiday_set(employee, from_date, to_date)
	leaves = get_leave_map(employee, from_date, to_date)
	checkins = get_checkins(employee, from_date, to_date)

	count, d = 0, from_date
	while d <= to_date:
		values = compute_day(emp, d, holidays=holidays, leaves=leaves, checkins=checkins.get(d, []))
		# Skip empty future-less days without anything to say (keeps the table small)
		if (
			values.worked_hours
			or values.expected_hours
			or values.day_type != "Weekly Off"
			or frappe.db.exists("Employee Work Log", {"employee": employee, "date": d})
		):
			upsert_log(values)
			count += 1
		d = add_days(d, 1)

	if update_summary:
		update_employee_summary(employee)
	return count


def update_employee_summary(employee: str):
	meta = frappe.get_meta("Employee")
	if not meta.has_field("moon_hours_this_week"):
		return
	today = getdate(nowdate())
	week_start = add_days(today, -today.weekday())
	month_start = today.replace(day=1)

	def total(field, since):
		return flt(
			frappe.db.sql(
				f"select sum({field}) from `tabEmployee Work Log` where employee=%s and date between %s and %s",
				(employee, since, today),
			)[0][0]
		)

	emp = get_employee_row(employee)
	frappe.db.set_value(
		"Employee",
		employee,
		{
			"moon_effective_daily_hours": flt(get_employee_policy(emp).daily_hours),
			"moon_hours_this_week": round(total("worked_hours", week_start), 2),
			"moon_expected_this_week": round(total("expected_hours", week_start), 2),
			"moon_hours_this_month": round(total("worked_hours", month_start), 2),
			"moon_expected_this_month": round(total("expected_hours", month_start), 2),
			"moon_overtime_this_month": round(total("overtime_hours", month_start), 2),
		},
		update_modified=False,
	)


# --------------------------------------------------------------------------- public API / hooks
@frappe.whitelist()
def recalculate(
	from_date: str | None = None,
	to_date: str | None = None,
	employee: str | None = None,
	company: str | None = None,
	department: str | None = None,
):
	"""Recalculate work logs. HR users can run it for everyone, employees only for themselves."""
	from_date = getdate(from_date or add_days(nowdate(), -30))
	to_date = getdate(to_date or nowdate())
	if not frappe.has_permission("Employee Work Log", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	filters = {"status": "Active"}
	if employee:
		filters["name"] = employee
	if company:
		filters["company"] = company
	if department:
		filters["department"] = department
	employees = frappe.get_all("Employee", filters=filters, pluck="name")

	if len(employees) * ((to_date - from_date).days + 1) > 3000:
		frappe.enqueue(
			_recalculate_many, queue="long", employees=employees, from_date=from_date, to_date=to_date
		)
		return {"queued": True, "employees": len(employees)}

	total = sum(recalculate_employee(e, from_date, to_date) for e in employees)
	return {"queued": False, "employees": len(employees), "days": total}


def _recalculate_many(employees, from_date, to_date):
	for e in employees:
		recalculate_employee(e, from_date, to_date)
		frappe.db.commit()


@frappe.whitelist()
def get_my_hours(employee: str | None = None):
	"""Small summary used by the Employee form banner."""
	employee = employee or frappe.db.get_value("Employee", {"user_id": frappe.session.user})
	if not employee:
		return {}
	frappe.has_permission("Employee", "read", employee, throw=True)
	emp = get_employee_row(employee)
	policy = get_employee_policy(emp)
	today = compute_day(emp, nowdate())
	return {
		"policy": policy.name,
		"daily_hours": flt(policy.daily_hours),
		"weekly_hours": flt(policy.daily_hours) * sum(cint(policy.get(d)) for d in DAY_FIELDS),
		"today_worked": today.worked_hours,
		"today_status": today.status,
	}


def on_checkin_change(doc, method=None):
	if frappe.flags.in_import or frappe.flags.moon_skip_work_log or frappe.flags.in_install:
		return
	day = getdate(doc.shift_start) if doc.get("shift_start") else getdate(doc.time)
	frappe.enqueue(
		recalculate_employee,
		queue="short",
		employee=doc.employee,
		from_date=day,
		to_date=day,
		enqueue_after_commit=True,
		deduplicate=True,
		job_id=f"moon-wl-{doc.employee}-{day}",
	)


def refresh_today():
	for e in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
		recalculate_employee(e, nowdate(), nowdate())


def refresh_recent_days():
	"""Nightly: close out the last few days (late check-outs, approved leave, holidays)."""
	for e in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
		recalculate_employee(e, add_days(nowdate(), -7), nowdate())
