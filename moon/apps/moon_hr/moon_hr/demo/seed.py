# Copyright (c) 2026, Moon Exchange
"""Seed the Moon Exchange demo across every Frappe HR feature plus the moon_hr add-ons.

    bench --site moon.localhost execute moon_hr.demo.seed.run

Each step is idempotent and recorded once it succeeds, so a failed run can simply be re-run.
All dates are relative to the day the seed runs.
"""

from __future__ import annotations

import json
import random
import traceback
from datetime import datetime, timedelta

import frappe
from frappe.utils import (
	add_days,
	add_months,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	now_datetime,
	nowdate,
)

from moon_hr.data.team import COFOUNDERS, LEADERSHIP
from moon_hr.demo import data as D
from moon_hr.demo.setup import ABBR, COMPANY, fiscal_year_dates

R = random.Random(2026)
TODAY = getdate(nowdate())
WINDOW_DAYS = 35  # check-in history
STEPS_KEY = "moon_demo_steps"


# =============================================================== helpers
def dept(name):
	return f"{name} - {ABBR}"


def emp_id(key):
	return (
		frappe.db.get_value("Employee", {"moon_demo_key": key})
		if frappe.get_meta("Employee").has_field("moon_demo_key")
		else None
	)


def user_of(key):
	return frappe.db.get_value("User", f"{key}@{D.DEMO_DOMAIN}") and f"{key}@{D.DEMO_DOMAIN}"


def get_or_insert(doc: dict, key_filters: dict | None = None, submit=False):
	doctype = doc["doctype"]
	filters = key_filters or {k: v for k, v in doc.items() if k in ("name",)}
	existing = frappe.db.get_value(doctype, filters) if filters else None
	if existing:
		return frappe.get_doc(doctype, existing)
	d = frappe.get_doc(doc)
	d.insert(ignore_permissions=True)
	if submit:
		d.submit()
	return d


def prev_fy():
	start, _ = fiscal_year_dates()
	s = add_months(getdate(start), -12)
	return str(s), str(add_days(getdate(start), -1))


def fy_label(start):
	s = getdate(start)
	return f"{s.year}-{s.year + 1}"


_POLICY_CACHE: dict = {}


def working_day_for(emp, day):
	from moon_hr.moon_hr.work_hours import get_employee_policy, is_working_day

	if emp not in _POLICY_CACHE:
		_POLICY_CACHE[emp] = get_employee_policy(emp)
	return is_working_day(_POLICY_CACHE[emp], day)


def holidays_for(emp):
	from moon_hr.moon_hr.work_hours import get_holiday_set

	return get_holiday_set(emp, add_days(TODAY, -400), add_days(TODAY, 400))


def pick_working_days(emp, start, end, count, exclude=()):
	hol = holidays_for(emp)
	days, d = [], getdate(start)
	while d <= getdate(end):
		if working_day_for(emp, d) and d not in hol and d not in exclude:
			days.append(d)
		d = add_days(d, 1)
	return days[:count] if count else days


def done_steps():
	return set(json.loads(frappe.db.get_default(STEPS_KEY) or "[]"))


def mark_done(step):
	steps = done_steps()
	steps.add(step)
	frappe.db.set_default(STEPS_KEY, json.dumps(sorted(steps)))


# =============================================================== entry point
def is_seeded():
	return bool(frappe.db.get_default("moon_demo_seeded"))


def run(force: bool = False):
	frappe.set_user("Administrator")
	frappe.flags.mute_emails = True
	frappe.flags.moon_skip_work_log = True
	if is_seeded() and not force:
		print("Demo data already seeded - skipping. (run(force=True) to re-run missing steps)")
		return

	ensure_demo_key_field()
	failures = []
	for step in STEPS:
		name = step.__name__
		if name in done_steps():
			continue
		print(f"  - {name} ...", flush=True)
		try:
			step()
			mark_done(name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			failures.append(name)
			print(f"    !! {name} failed:\n{traceback.format_exc()}", flush=True)
			break  # later steps build on this one

	frappe.flags.moon_skip_work_log = False
	if failures:
		print(
			f"Demo seed finished with {len(failures)} failed step(s): {', '.join(failures)}. Re-run to retry."
		)
	else:
		frappe.db.set_default("moon_demo_seeded", "1")
		frappe.db.commit()
		print("Demo data seeded successfully.")


def ensure_demo_key_field():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	if not frappe.get_meta("Employee").has_field("moon_demo_key"):
		create_custom_fields(
			{
				"Employee": [
					dict(
						fieldname="moon_demo_key",
						label="Demo Key",
						fieldtype="Data",
						hidden=1,
						read_only=1,
						insert_after="moon_overtime_this_month",
						no_copy=1,
					)
				]
			}
		)
		frappe.clear_cache(doctype="Employee")


# =============================================================== 1. organisation
def org_structure():
	for b in D.BRANCHES:
		get_or_insert({"doctype": "Branch", "branch": b}, {"name": b})
	for d in D.DEPARTMENTS:
		if not frappe.db.exists("Department", dept(d)):
			frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": d,
					"company": COMPANY,
					"parent_department": "All Departments",
				}
			).insert(ignore_permissions=True)
	for d in D.DESIGNATIONS:
		get_or_insert({"doctype": "Designation", "designation_name": d}, {"name": d})
	for g, base in (
		("L1 Associate", 30000),
		("L2 Specialist", 90000),
		("L3 Senior", 180000),
		("L4 Lead", 280000),
		("L5 Leadership", 0),
	):
		get_or_insert({"doctype": "Employee Grade", "__newname": g, "default_base_pay": base}, {"name": g})

	# Company profile
	company = frappe.get_doc("Company", COMPANY)
	company.update(
		{
			"company_description": "FIU-IND registered crypto exchange made for Indian traders.",
			"website": "https://moon.exchange",
			"country": "India",
			"default_currency": "INR",
		}
	)
	company.save(ignore_permissions=True)

	# HR settings tuned for the demo
	hr = frappe.get_single("HR Settings")
	hr.update(
		{
			"leave_approver_mandatory_in_leave_application": 0,
			"expense_approver_mandatory_in_expense_claim": 0,
			"allow_geolocation_tracking": 0,
			"standard_working_hours": 8,
			"emp_created_by": "Naming Series",
			"send_birthday_reminders": 0,
			"send_work_anniversary_reminders": 0,
			"send_holiday_reminders": 0,
		}
	)
	hr.save(ignore_permissions=True)


def fiscal_years_and_holidays():
	cur_start, cur_end = fiscal_year_dates()
	p_start, p_end = prev_fy()
	for s, e in ((p_start, p_end), (cur_start, cur_end)):
		label = fy_label(s)
		if not frappe.db.exists("Fiscal Year", label) and not frappe.db.get_value(
			"Fiscal Year", {"year_start_date": s}
		):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": label,
					"year_start_date": s,
					"year_end_date": e,
					"companies": [{"company": COMPANY}],
				}
			).insert(ignore_permissions=True)

	festivals = {
		# variable-date festivals (approximate dates, demo only)
		"2025-03-14": "Holi",
		"2025-10-02": "Gandhi Jayanti / Dussehra",
		"2025-10-21": "Diwali",
		"2026-03-04": "Holi",
		"2026-09-14": "Ganesh Chaturthi",
		"2026-10-20": "Dussehra",
		"2026-11-09": "Diwali Holiday",
		"2027-03-22": "Holi",
		"2027-09-04": "Ganesh Chaturthi",
		"2027-10-09": "Dussehra",
		"2027-10-29": "Diwali",
		"2028-03-11": "Holi",
	}
	fixed = {
		"01-26": "Republic Day",
		"05-01": "Maharashtra Day",
		"08-15": "Independence Day",
		"10-02": "Gandhi Jayanti",
		"12-25": "Christmas",
	}

	def build(name, weekly_offs):
		if frappe.db.exists("Holiday List", name):
			return name
		hl = frappe.new_doc("Holiday List")
		hl.update({"holiday_list_name": name, "from_date": p_start, "to_date": cur_end, "color": "#F5C542"})
		seen = set()
		d = getdate(p_start)
		while d <= getdate(cur_end):
			desc = festivals.get(str(d)) or fixed.get(d.strftime("%m-%d"))
			if desc:
				hl.append("holidays", {"holiday_date": d, "description": desc, "weekly_off": 0})
				seen.add(d)
			elif d.strftime("%A") in weekly_offs:
				hl.append("holidays", {"holiday_date": d, "description": d.strftime("%A"), "weekly_off": 1})
			d = add_days(d, 1)
		hl.insert(ignore_permissions=True)
		return name

	office = build("Moon Exchange - Office (Sat & Sun off)", {"Saturday", "Sunday"})
	build("Moon Exchange - 24x7 Ops (Sun off)", {"Sunday"})
	frappe.db.set_value("Company", COMPANY, "default_holiday_list", office)
	if frappe.db.exists("DocType", "Holiday List Assignment"):
		if not frappe.db.exists("Holiday List Assignment", {"assigned_to": COMPANY, "docstatus": 1}):
			hla = frappe.get_doc(
				{
					"doctype": "Holiday List Assignment",
					"applicable_for": "Company",
					"assigned_to": COMPANY,
					"holiday_list": office,
					"from_date": p_start,
				}
			)
			hla.insert(ignore_permissions=True)
			hla.submit()


def shifts_and_locations():
	get_or_insert(
		{
			"doctype": "Shift Location",
			"location_name": "Bengaluru HQ",
			"latitude": 12.9352,
			"longitude": 77.6245,
			"checkin_radius": 300,
		},
		{"name": "Bengaluru HQ"},
	)
	get_or_insert(
		{
			"doctype": "Shift Location",
			"location_name": "Mumbai Office",
			"latitude": 19.0607,
			"longitude": 72.8362,
			"checkin_radius": 300,
		},
		{"name": "Mumbai Office"},
	)
	office = frappe.db.get_value("Company", COMPANY, "default_holiday_list")
	for name, (start, end) in D.SHIFTS.items():
		if frappe.db.exists("Shift Type", name):
			continue
		st = frappe.new_doc("Shift Type")
		st.update(
			{
				"__newname": name,
				"name": name,
				"start_time": start,
				"end_time": end,
				"holiday_list": "Moon Exchange - 24x7 Ops (Sun off)" if name.startswith("Ops") else office,
				"enable_auto_attendance": 1,
				"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
				"working_hours_calculation_based_on": "Every Valid Check-in and Check-out",
				"begin_check_in_before_shift_start_time": 120,
				"allow_check_out_after_shift_end_time": 240,
				"working_hours_threshold_for_half_day": 4 if "Half" not in name else 2,
				"working_hours_threshold_for_absent": 1.5 if "Half" not in name else 1,
				"enable_late_entry_marking": 1,
				"late_entry_grace_period": 15,
				"enable_early_exit_marking": 1,
				"early_exit_grace_period": 15,
				"mark_auto_attendance_on_holidays": 1 if name.startswith("Ops") else 0,
				"color": "Blue" if name.startswith("Ops") else "Green",
			}
		)
		st.insert(ignore_permissions=True)


# =============================================================== 2. people
def users_and_employees():
	ensure_demo_key_field()
	placeholder_dob = "1990-01-01"
	placeholder_doj = "2025-01-06"

	def person_bio(full):
		for p in COFOUNDERS + LEADERSHIP:
			if p["name"] == full:
				return p
		return {}

	# -- founders & leadership first (no payroll / attendance in the demo)
	for key, team_name, first, last, department, designation, _rt in D.LEADERS:
		if emp_id(key):
			continue
		p = person_bio(team_name)
		bio = f"<p>{p.get('bio', '')}</p><p><b>{p.get('role', '')}</b> · {' · '.join(p.get('tags', []))}</p>"
		e = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first,
				"last_name": last,
				"company": COMPANY,
				"gender": "Prefer not to say",
				"date_of_birth": placeholder_dob,
				"date_of_joining": placeholder_doj,
				"department": dept(department),
				"designation": designation,
				"employment_type": "Full-time",
				"branch": "Bengaluru HQ",
				"grade": "L5 Leadership",
				"status": "Active",
				"bio": bio,
				"company_email": f"{key}@{D.DEMO_DOMAIN}",
				"prefered_contact_email": "Company Email",
				"moon_demo_key": key,
			}
		)
		e.insert(ignore_permissions=True)
		e.add_comment(
			"Comment",
			"Demo placeholders: date of birth, joining date and gender are not from the "
			"founders board. Please update them from the real records.",
		)

	# -- staff (fictional)
	staff = [*D.EMPLOYEES, D.LEFT_EMPLOYEE]
	for (
		key,
		first,
		last,
		gender,
		department,
		designation,
		etype,
		branch,
		shift,
		_rt,
		months,
		ctc,
		extra,
	) in staff:
		if emp_id(key):
			continue
		doj = add_months(TODAY, -months)
		doj = add_days(doj, -R.randint(0, 20))
		dob = add_days(getdate(f"{R.randint(1988, 2004)}-01-01"), R.randint(0, 360))
		if etype == "Intern":
			dob = add_days(getdate(f"{R.randint(2002, 2005)}-01-01"), R.randint(0, 360))
		grade = (
			"L1 Associate"
			if ctc < 60000
			else "L2 Specialist"
			if ctc < 150000
			else "L3 Senior"
			if ctc < 260000
			else "L4 Lead"
		)
		doc = {
			"doctype": "Employee",
			"first_name": first,
			"last_name": last,
			"company": COMPANY,
			"gender": gender,
			"date_of_birth": dob,
			"date_of_joining": doj,
			"department": dept(department),
			"designation": designation,
			"employment_type": etype,
			"branch": branch,
			"grade": grade,
			"default_shift": shift,
			"status": "Active",
			"company_email": f"{key}@{D.DEMO_DOMAIN}",
			"prefered_contact_email": "Company Email",
			"cell_number": f"+91 9{R.randint(100000000, 999999999)}",
			"ctc": ctc * 12,
			"salary_currency": "INR",
			"salary_mode": "Bank",
			"moon_demo_key": key,
		}
		if extra.get("policy"):
			doc["moon_work_hour_policy"] = extra["policy"]
		if extra.get("daily_hours"):
			doc["moon_daily_hours_override"] = extra["daily_hours"]
		e = frappe.get_doc(doc)
		e.insert(ignore_permissions=True)
		if extra.get("note"):
			e.add_comment("Comment", extra["note"])

	# -- reporting lines
	for row in [*D.EMPLOYEES, D.LEFT_EMPLOYEE]:
		key, rt = row[0], row[9]
		if rt and emp_id(rt):
			frappe.db.set_value("Employee", emp_id(key), "reports_to", emp_id(rt))

	# -- ops staff use the 24x7 holiday list
	if frappe.db.exists("DocType", "Holiday List Assignment"):
		for row in D.EMPLOYEES:
			if row[12].get("policy") == D.OPS_POLICY:
				e = emp_id(row[0])
				if not frappe.db.exists("Holiday List Assignment", {"assigned_to": e, "docstatus": 1}):
					hla = frappe.get_doc(
						{
							"doctype": "Holiday List Assignment",
							"applicable_for": "Employee",
							"assigned_to": e,
							"holiday_list": "Moon Exchange - 24x7 Ops (Sun off)",
							"from_date": max(
								getdate(frappe.db.get_value("Employee", e, "date_of_joining")),
								getdate(prev_fy()[0]),
							),
						}
					)
					hla.insert(ignore_permissions=True)
					hla.submit()
	else:
		for row in D.EMPLOYEES:
			if row[12].get("policy") == D.OPS_POLICY:
				frappe.db.set_value(
					"Employee", emp_id(row[0]), "holiday_list", "Moon Exchange - 24x7 Ops (Sun off)"
				)

	# -- separated employee
	left = emp_id(D.LEFT_EMPLOYEE[0])
	frappe.db.set_value(
		"Employee",
		left,
		{
			"status": "Left",
			"relieving_date": add_days(TODAY, -21),
			"reason_for_leaving": "Moved to a different city",
			"resignation_letter_date": add_days(TODAY, -51),
		},
	)

	# -- users for logging in to the demo
	from frappe.utils.password import update_password

	for row in D.EMPLOYEES:
		key, first, last, roles = row[0], row[1], row[2], row[12].get("user_roles")
		if not roles:
			continue
		email = f"{key}@{D.DEMO_DOMAIN}"
		if not frappe.db.exists("User", email):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": first,
					"last_name": last,
					"send_welcome_email": 0,
					"user_type": "System User",
					"roles": [{"role": r} for r in roles],
				}
			)
			u.flags.no_welcome_mail = True
			u.insert(ignore_permissions=True)
			update_password(email, D.DEMO_PASSWORD)
		e = frappe.get_doc("Employee", emp_id(key))
		if not e.user_id:
			e.user_id = email
			e.create_user_permission = 0 if "HR Manager" in roles else 1
			e.save(ignore_permissions=True)

	# leave / expense approvers follow the reporting line where the manager has a login
	for row in D.EMPLOYEES:
		e = frappe.get_doc("Employee", emp_id(row[0]))
		mgr_user = frappe.db.get_value("Employee", e.reports_to, "user_id") if e.reports_to else None
		approver = mgr_user or user_of("swati")
		if approver and approver != e.user_id:
			e.db_set(
				{"leave_approver": approver, "expense_approver": approver, "shift_request_approver": approver}
			)


def staff():
	"""Active, fictional employees -> list of dicts."""
	keys = [r[0] for r in D.EMPLOYEES]
	return [frappe._dict(key=k, name=emp_id(k), row=r) for k, r in zip(keys, D.EMPLOYEES, strict=False)]


# =============================================================== 3. leave
def leave_setup():
	cur_start, cur_end = fiscal_year_dates()
	p_start, p_end = prev_fy()
	for lt, extra in (
		("Casual Leave", {"max_continuous_days_allowed": 3}),
		("Sick Leave", {}),
		("Privilege Leave", {"is_carry_forward": 1, "allow_encashment": 1}),
	):
		frappe.db.set_value("Leave Type", lt, extra) if extra else None
	if not frappe.db.exists("Leave Type", "Crypto Wellness Day"):
		frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Crypto Wellness Day",
				"max_leaves_allowed": 2,
				"include_holiday": 0,
				"is_earned_leave": 0,
			}
		).insert(ignore_permissions=True)

	policies = {
		"Moon Standard": [
			("Casual Leave", 12),
			("Sick Leave", 8),
			("Privilege Leave", 18),
			("Crypto Wellness Day", 2),
		],
		"Moon Intern": [("Casual Leave", 6), ("Sick Leave", 4)],
		"Moon Part-time": [("Casual Leave", 6), ("Sick Leave", 6), ("Privilege Leave", 9)],
	}
	for title, details in policies.items():
		if not frappe.db.exists("Leave Policy", {"title": title, "docstatus": 1}):
			lp = frappe.get_doc(
				{
					"doctype": "Leave Policy",
					"title": title,
					"leave_policy_details": [{"leave_type": lt, "annual_allocation": n} for lt, n in details],
				}
			)
			lp.insert(ignore_permissions=True)
			lp.submit()

	for s, e in ((p_start, p_end), (cur_start, cur_end)):
		if not frappe.db.exists("Leave Period", {"from_date": s, "company": COMPANY}):
			frappe.get_doc(
				{"doctype": "Leave Period", "from_date": s, "to_date": e, "company": COMPANY, "is_active": 1}
			).insert(ignore_permissions=True)

	for s in staff():
		etype = s.row[6]
		policy_title = (
			"Moon Intern"
			if etype == "Intern"
			else "Moon Part-time"
			if etype == "Part-time"
			else "Moon Standard"
		)
		policy = frappe.db.get_value("Leave Policy", {"title": policy_title, "docstatus": 1})
		doj = getdate(frappe.db.get_value("Employee", s.name, "date_of_joining"))
		for fs, fe in ((p_start, p_end), (cur_start, cur_end)):
			if (getdate(fe) - max(doj, getdate(fs))).days < 120:
				continue  # joined too close to the period end for a full allocation
			if frappe.db.exists(
				"Leave Policy Assignment",
				{
					"employee": s.name,
					"effective_from": [">=", fs],
					"effective_to": ["<=", fe],
					"docstatus": 1,
				},
			):
				continue
			lpa = frappe.get_doc(
				{
					"doctype": "Leave Policy Assignment",
					"employee": s.name,
					"leave_policy": policy,
					"effective_from": max(doj, getdate(fs)),
					"effective_to": fe,
					"assignment_based_on": "",
				}
			)
			lpa.insert(ignore_permissions=True)
			lpa.submit()


def leave_applications():
	window_start = add_days(TODAY, -WINDOW_DAYS)
	plans = [
		# key, leave type, offset from window start (working-day index), days, status, half_day, reason
		("kavya", "Casual Leave", 6, 1, "Approved", 0, "Family function"),
		("rohan", "Sick Leave", 12, 2, "Approved", 0, "Viral fever"),
		("imran", "Privilege Leave", 18, 3, "Approved", 0, "Trip to Coorg"),
		("vikram", "Casual Leave", 9, 1, "Approved", 1, "Bank work - half day"),
		("meera", "Privilege Leave", 3, 2, "Approved", 0, "Wedding in the family"),
		("ritu", "Sick Leave", 15, 1, "Approved", 0, "Migraine"),
		("divya", "Crypto Wellness Day", 20, 1, "Approved", 0, "Wellness day"),
		("sneha", "Casual Leave", 22, 1, "Rejected", 0, "Personal work (release week - rejected)"),
	]
	future = [
		("arjun", "Privilege Leave", 8, 3, "Open", "Year-end vacation"),
		("nidhi", "Casual Leave", 3, 1, "Open", "Personal work"),
		("karan", "Privilege Leave", 12, 2, "Open", "Hometown visit"),
		("gaurav", "Casual Leave", 5, 1, "Approved", "Tax filing appointment"),
	]
	for key, lt, idx, days, status, half, reason in plans:
		e = emp_id(key)
		if frappe.db.exists("Leave Application", {"employee": e, "description": reason}):
			continue
		wd = pick_working_days(e, window_start, add_days(TODAY, -1), 0)
		if len(wd) <= idx + days:
			continue
		_make_leave(e, lt, wd[idx], wd[idx + days - 1], status, half, reason)
	for key, lt, ahead, days, status, reason in future:
		e = emp_id(key)
		if frappe.db.exists("Leave Application", {"employee": e, "description": reason}):
			continue
		wd = pick_working_days(e, add_days(TODAY, ahead), add_days(TODAY, ahead + 20), days)
		if len(wd) < days:
			continue
		_make_leave(e, lt, wd[0], wd[-1], status, 0, reason)


def _make_leave(employee, leave_type, from_date, to_date, status, half_day, reason):
	la = frappe.get_doc(
		{
			"doctype": "Leave Application",
			"employee": employee,
			"leave_type": leave_type,
			"company": COMPANY,
			"from_date": from_date,
			"to_date": to_date,
			"half_day": half_day,
			"half_day_date": from_date if half_day else None,
			"posting_date": add_days(from_date, -3) if from_date < TODAY else TODAY,
			"status": status,
			"description": reason,
			"follow_via_email": 0,
		}
	)
	la.insert(ignore_permissions=True)
	if status in ("Approved", "Rejected"):
		la.submit()


# =============================================================== 4. attendance & time
def shift_assignments_and_requests():
	for s in staff():
		extra = s.row[12]
		if extra.get("policy") != D.OPS_POLICY:
			continue
		if frappe.db.exists("Shift Assignment", {"employee": s.name, "docstatus": 1}):
			continue
		sa = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": s.name,
				"company": COMPANY,
				"shift_type": s.row[8],
				"start_date": add_days(TODAY, -WINDOW_DAYS - 10),
				"status": "Active",
				"shift_location": "Bengaluru HQ",
			}
		)
		sa.insert(ignore_permissions=True)
		sa.submit()

	# pending shift swap request
	pooja = emp_id("pooja")
	if not frappe.db.exists("Shift Request", {"employee": pooja}):
		frappe.get_doc(
			{
				"doctype": "Shift Request",
				"employee": pooja,
				"company": COMPANY,
				"shift_type": "Ops Morning 06:00-14:00",
				"from_date": add_days(TODAY, 7),
				"to_date": add_days(TODAY, 13),
				"status": "Draft",
				"approver": user_of("swati") or "Administrator",
			}
		).insert(ignore_permissions=True)


WFH_PLAN = {"sneha": [4, 11, 19], "kavya": [14], "aisha": [8], "meera": [10]}


def attendance_requests():
	window_start = add_days(TODAY, -WINDOW_DAYS)
	for key, idxs in WFH_PLAN.items():
		e = emp_id(key)
		leaves = _leave_days(e)
		wd = pick_working_days(e, window_start, add_days(TODAY, -1), 0, exclude=leaves)
		for i in idxs:
			if i >= len(wd) or frappe.db.exists("Attendance Request", {"employee": e, "from_date": wd[i]}):
				continue
			ar = frappe.get_doc(
				{
					"doctype": "Attendance Request",
					"employee": e,
					"company": COMPANY,
					"from_date": wd[i],
					"to_date": wd[i],
					"reason": "Work From Home",
					"explanation": "Internet installation at home" if i % 2 else "Waiting for a delivery",
				}
			)
			ar.insert(ignore_permissions=True)
			ar.submit()
	# one On Duty request (conference)
	ana = emp_id("ananya")
	wd = pick_working_days(
		ana, add_days(TODAY, -WINDOW_DAYS), add_days(TODAY, -1), 0, exclude=_leave_days(ana)
	)
	if wd and not frappe.db.exists("Attendance Request", {"employee": ana, "reason": "On Duty"}):
		ar = frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": ana,
				"company": COMPANY,
				"from_date": wd[5],
				"to_date": wd[5],
				"reason": "On Duty",
				"explanation": "FIU-IND compliance workshop, New Delhi",
			}
		)
		ar.insert(ignore_permissions=True)
		ar.submit()


def _leave_days(employee):
	from moon_hr.moon_hr.work_hours import get_leave_map

	return set(get_leave_map(employee, add_days(TODAY, -400), add_days(TODAY, 400)).keys())


def _attendance_days(employee):
	return {
		getdate(d)
		for d in frappe.get_all(
			"Attendance", filters={"employee": employee, "docstatus": 1}, pluck="attendance_date"
		)
	}


def checkins():
	"""Realistic clock-in / clock-out history from the employee's own shift and work-hour policy."""
	from moon_hr.moon_hr.work_hours import get_employee_policy

	frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
	window_start = add_days(TODAY, -WINDOW_DAYS)
	now = now_datetime()
	for s in staff():
		e = s.name
		if frappe.db.exists("Employee Checkin", {"employee": e}):
			continue  # already generated (re-run)
		key, dept_name, branch, shift = s.key, s.row[4], s.row[7], s.row[8]
		policy = get_employee_policy(e)
		start_t, end_t = D.SHIFTS[shift]
		start_h, start_m = int(start_t[:2]), int(start_t[3:5])
		doj = getdate(frappe.db.get_value("Employee", e, "date_of_joining"))
		hol = holidays_for(e)
		skip = _leave_days(e) | _attendance_days(e)
		hard_worker = dept_name in ("Engineering", "Trading Operations") or key in ("ananya", "swati")
		device = {"Bengaluru HQ": "BLR-HQ-Biometric-01", "Mumbai Office": "MUM-Biometric-01"}.get(
			branch, "Moon HR App"
		)
		lat, lng = {"Bengaluru HQ": (12.9352, 77.6245), "Mumbai Office": (19.0607, 72.8362)}.get(
			branch, (None, None)
		)
		works_holidays = s.row[12].get("policy") == D.OPS_POLICY

		d = window_start
		while d <= TODAY:
			is_hol = d in hol
			if (
				d < doj
				or d in skip
				or not working_day_for(e, d)
				or (is_hol and not (works_holidays and R.random() < 0.5))
			):
				d = add_days(d, 1)
				continue
			if R.random() < 0.035 and d < TODAY:  # unplanned absence
				d = add_days(d, 1)
				continue

			arrive = datetime(d.year, d.month, d.day, start_h, start_m) + timedelta(minutes=R.gauss(-2, 7))
			roll = R.random()
			if roll < 0.10:
				arrive += timedelta(minutes=R.randint(25, 70))  # late
			elif roll < 0.18:
				arrive -= timedelta(minutes=R.randint(10, 25))  # early bird

			target = flt(policy.daily_hours) + R.gauss(0.05, 0.22)
			roll = R.random()
			if roll < (0.16 if hard_worker else 0.06):
				target += R.uniform(1, 2.75)  # overtime
			elif roll < 0.24:
				target -= R.uniform(0.75, 2)  # left early
			elif roll < 0.27 and policy.daily_hours >= 6:
				target = flt(policy.half_day_threshold) - 0.5  # half day
			target = max(target, 0.75)

			logs = []
			if target >= 7 and R.random() < 0.6:  # logged lunch break
				first = target * R.uniform(0.42, 0.55)
				brk = timedelta(minutes=R.randint(30, 55))
				out1 = arrive + timedelta(hours=first)
				in2 = out1 + brk
				logs = [
					("IN", arrive),
					("OUT", out1),
					("IN", in2),
					("OUT", in2 + timedelta(hours=target - first)),
				]
			else:
				# an unlogged break that the policy auto-deducts is spent at the office too
				span = target + (flt(policy.auto_break_minutes) / 60 if target > 5 else 0)
				logs = [("IN", arrive), ("OUT", arrive + timedelta(hours=span))]

			for log_type, t in logs:
				if t > now:
					break  # today: still clocked in
				doc = frappe.get_doc(
					{
						"doctype": "Employee Checkin",
						"employee": e,
						"time": t.replace(microsecond=0),
						"log_type": log_type,
						"device_id": device if t.hour % 3 else "Moon HR App",
					}
				)
				if device == "Moon HR App" or doc.device_id == "Moon HR App":
					if lat:
						doc.latitude, doc.longitude = (
							lat + R.uniform(-0.001, 0.001),
							lng + R.uniform(-0.001, 0.001),
						)
				doc.insert(ignore_permissions=True)
			d = add_days(d, 1)
		frappe.db.commit()


def auto_attendance():
	window_start = add_days(TODAY, -WINDOW_DAYS)
	for name in D.SHIFTS:
		st = frappe.get_doc("Shift Type", name)
		st.db_set(
			{
				"process_attendance_after": add_days(window_start, -1),
				"last_sync_of_checkin": now_datetime().replace(hour=0, minute=0, second=0, microsecond=0),
			}
		)
		st.reload()
		st.process_auto_attendance()
		frappe.db.commit()


def compensatory_leave():
	"""Ops staff who worked on a public holiday claim a compensatory off."""
	ops = [s for s in staff() if s.row[12].get("policy") == D.OPS_POLICY]
	for s in ops:
		hol = holidays_for(s.name)
		worked = frappe.get_all(
			"Attendance",
			filters={
				"employee": s.name,
				"docstatus": 1,
				"status": "Present",
				"attendance_date": ["in", [str(h) for h in hol]] if hol else ["is", "not set"],
			},
			pluck="attendance_date",
		)
		worked = [w for w in worked if frappe.db.get_value("Holiday", {"holiday_date": w, "weekly_off": 0})]
		if not worked or frappe.db.exists("Compensatory Leave Request", {"employee": s.name}):
			continue
		clr = frappe.get_doc(
			{
				"doctype": "Compensatory Leave Request",
				"employee": s.name,
				"leave_type": "Compensatory Off",
				"work_from_date": worked[0],
				"work_end_date": worked[0],
				"reason": "Covered the trading desk on a public holiday",
			}
		)
		clr.insert(ignore_permissions=True)
		clr.submit()


def work_hours():
	"""Person-specific work logs (moon_hr) computed from the check-ins above."""
	from moon_hr.moon_hr.work_hours import recalculate_employee

	for s in staff():
		recalculate_employee(s.name, add_days(TODAY, -WINDOW_DAYS), TODAY)
	# a manual correction example
	e = emp_id("aditya")
	log = frappe.db.get_value(
		"Employee Work Log", {"employee": e, "status": ["in", ["Absent", "Short"]]}, "name"
	)
	if log:
		doc = frappe.get_doc("Employee Work Log", log)
		doc.is_manual = 1
		doc.worked_hours = 9
		doc.notes = "Production incident handled remotely; hours confirmed by the engineering manager."
		doc.save(ignore_permissions=True)


# =============================================================== 5. payroll
def payroll_setup():
	parent_tax = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_name": "Duties and Taxes", "is_group": 1}
	)
	parent_payable = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_name": "Accounts Payable", "is_group": 1}
	)
	parent_bank = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_name": "Bank Accounts", "is_group": 1}
	)

	def account(name, parent, account_type="", root="Liability"):
		full = f"{name} - {ABBR}"
		if not frappe.db.exists("Account", full):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": name,
					"parent_account": parent,
					"company": COMPANY,
					"account_type": account_type,
					"root_type": root,
				}
			).insert(ignore_permissions=True)
		return full

	pf = account("PF Payable", parent_tax, "Tax")
	pt = account("Professional Tax Payable", parent_tax, "Tax")
	tds = account("TDS Payable (Salary)", parent_tax, "Tax")
	reimb = account("Employee Reimbursements Payable", parent_payable, "Payable")
	bank = account("Payroll Bank Account", parent_bank, "Bank", "Asset")
	frappe.db.set_value(
		"Company",
		COMPANY,
		{
			"default_expense_claim_payable_account": reimb,
			"default_payroll_payable_account": f"Payroll Payable - {ABBR}",
			"default_bank_account": bank,
		},
	)

	# demo: don't e-mail PDF payslips (needs SMTP + a PDF renderer)
	frappe.db.set_single_value(
		"Payroll Settings", {"email_salary_slip_to_employee": 0, "show_leave_balances_in_salary_slip": 1}
	)
	salary_acc = f"Salary - {ABBR}"
	components = {
		# name: (abbr, type, account, extra)
		"Basic": ("B", "Earning", salary_acc, {}),
		"House Rent Allowance": ("HRA", "Earning", salary_acc, {}),
		"Special Allowance": ("SA", "Earning", salary_acc, {}),
		"Stipend": ("STP", "Earning", salary_acc, {}),
		"Performance Bonus": ("PB", "Earning", salary_acc, {}),
		"Referral Bonus": ("RB", "Earning", salary_acc, {}),
		"Retention Bonus": ("RTB", "Earning", salary_acc, {}),
		"Provident Fund": ("PF", "Deduction", pf, {}),
		"Professional Tax": ("PT", "Deduction", pt, {}),
		"Income Tax": (
			"IT",
			"Deduction",
			tds,
			{"variable_based_on_taxable_salary": 1, "is_income_tax_component": 1},
		),
	}
	for name, (abbr, ctype, acc, extra) in components.items():
		if frappe.db.exists("Salary Component", name):
			comp = frappe.get_doc("Salary Component", name)
		else:
			comp = frappe.new_doc("Salary Component")
			comp.salary_component = name
			comp.salary_component_abbr = abbr
			comp.type = ctype
		comp.update(extra)
		comp.depends_on_payment_days = (
			1 if name in ("Basic", "House Rent Allowance", "Special Allowance", "Stipend") else 0
		)
		if not any(a.company == COMPANY for a in comp.get("accounts", [])):
			comp.append("accounts", {"company": COMPANY, "account": acc})
		comp.save(ignore_permissions=True)
	return {"bank": bank}


def _abbr(name):
	return frappe.db.get_value("Salary Component", name, "salary_component_abbr")


def salary_structures():
	b, hra, sa, pf, pt = (
		_abbr(x)
		for x in ("Basic", "House Rent Allowance", "Special Allowance", "Provident Fund", "Professional Tax")
	)
	structures = {
		"Moon Standard CTC": {
			"earnings": [
				{
					"salary_component": "Basic",
					"abbr": b,
					"amount_based_on_formula": 1,
					"formula": "base * 0.5",
				},
				{
					"salary_component": "House Rent Allowance",
					"abbr": hra,
					"amount_based_on_formula": 1,
					"formula": "base * 0.2",
				},
				{
					"salary_component": "Special Allowance",
					"abbr": sa,
					"amount_based_on_formula": 1,
					"formula": "base * 0.3",
				},
			],
			"deductions": [
				{
					"salary_component": "Provident Fund",
					"abbr": pf,
					"amount_based_on_formula": 1,
					"formula": f"({b} * 0.12) if ({b} * 0.12) < 1800 else 1800",
				},
				{
					"salary_component": "Professional Tax",
					"abbr": pt,
					"amount": 200,
					"condition": "base > 15000",
				},
				{"salary_component": "Income Tax", "abbr": _abbr("Income Tax")},
			],
		},
		"Moon Intern Stipend": {
			"earnings": [
				{
					"salary_component": "Stipend",
					"abbr": _abbr("Stipend"),
					"amount_based_on_formula": 1,
					"formula": "base",
				}
			],
			"deductions": [],
		},
	}
	for name, rows in structures.items():
		if frappe.db.exists("Salary Structure", {"name": name, "docstatus": 1}):
			continue
		ss = frappe.get_doc(
			{
				"doctype": "Salary Structure",
				"name": name,
				"__newname": name,
				"company": COMPANY,
				"currency": "INR",
				"is_active": "Yes",
				"payroll_frequency": "Monthly",
				"payment_account": frappe.db.get_value("Company", COMPANY, "default_bank_account"),
				**rows,
			}
		)
		ss.insert(ignore_permissions=True)
		ss.submit()

	# payroll periods + income tax slab (new regime, demo approximation)
	slabs = [
		(0, 400000, 0),
		(400000, 800000, 5),
		(800000, 1200000, 10),
		(1200000, 1600000, 15),
		(1600000, 2000000, 20),
		(2000000, 2400000, 25),
		(2400000, 0, 30),
	]
	p_start, _ = prev_fy()
	slab_name = "New Tax Regime (demo)"
	if not frappe.db.exists("Income Tax Slab", {"name": slab_name}):
		its = frappe.get_doc(
			{
				"doctype": "Income Tax Slab",
				"__newname": slab_name,
				"name": slab_name,
				"effective_from": p_start,
				"currency": "INR",
				"company": COMPANY,
				"standard_tax_exemption_amount": 75000,
				"allow_tax_exemption": 0,
				"slabs": [
					{
						"from_amount": f,
						"to_amount": t,
						"percent_deduction": p,
						"condition": "annual_taxable_earning > 1200000" if p else None,
					}
					for f, t, p in slabs
				],
				"other_taxes_and_charges": [{"description": "Health & Education Cess", "percent": 4}],
			}
		)
		its.insert(ignore_permissions=True)
		its.submit()

	for s, e in (prev_fy(), fiscal_year_dates()):
		name = f"FY {fy_label(s)}"
		if not frappe.db.exists("Payroll Period", name):
			pp = frappe.get_doc(
				{
					"doctype": "Payroll Period",
					"__newname": name,
					"name": name,
					"company": COMPANY,
					"start_date": s,
					"end_date": e,
				}
			)
			pp.insert(ignore_permissions=True)


def salary_assignments():
	p_start, _ = prev_fy()
	slab = frappe.db.get_value("Income Tax Slab", {"docstatus": 1}, "name")
	for s in staff():
		if frappe.db.exists("Salary Structure Assignment", {"employee": s.name, "docstatus": 1}):
			continue
		etype, monthly = s.row[6], s.row[11]
		doj = getdate(frappe.db.get_value("Employee", s.name, "date_of_joining"))
		structure = "Moon Intern Stipend" if etype == "Intern" else "Moon Standard CTC"
		ssa = frappe.get_doc(
			{
				"doctype": "Salary Structure Assignment",
				"employee": s.name,
				"salary_structure": structure,
				"company": COMPANY,
				"currency": "INR",
				"from_date": max(doj, getdate(p_start)),
				"base": monthly,
				"variable": 0,
				"income_tax_slab": slab,
				"payroll_payable_account": f"Payroll Payable - {ABBR}",
			}
		)
		ssa.insert(ignore_permissions=True)
		ssa.submit()


def additional_pay():
	last_month_end = add_days(get_first_day(TODAY), -1)
	if not frappe.db.exists("Additional Salary", {"employee": emp_id("kavya")}):
		ad = frappe.get_doc(
			{
				"doctype": "Additional Salary",
				"employee": emp_id("kavya"),
				"company": COMPANY,
				"salary_component": "Performance Bonus",
				"currency": "INR",
				"amount": 50000,
				"payroll_date": add_days(last_month_end, -2),
				"overwrite_salary_structure_amount": 1,
			}
		)
		ad.insert(ignore_permissions=True)
		ad.submit()
	if not frappe.db.exists("Employee Incentive", {"employee": emp_id("arjun")}):
		inc = frappe.get_doc(
			{
				"doctype": "Employee Incentive",
				"employee": emp_id("arjun"),
				"company": COMPANY,
				"salary_component": "Referral Bonus",
				"currency": "INR",
				"incentive_amount": 25000,
				"payroll_date": add_days(last_month_end, -2),
			}
		)
		inc.insert(ignore_permissions=True)
		inc.submit()
	if not frappe.db.exists("Retention Bonus", {"employee": emp_id("imran")}):
		rb = frappe.get_doc(
			{
				"doctype": "Retention Bonus",
				"employee": emp_id("imran"),
				"company": COMPANY,
				"salary_component": "Retention Bonus",
				"bonus_amount": 150000,
				"currency": "INR",
				"bonus_payment_date": get_last_day(add_months(TODAY, 1)),
			}
		)
		rb.insert(ignore_permissions=True)
		rb.submit()


def payroll_runs():
	from hrms.payroll.doctype.payroll_entry.payroll_entry import (
		create_salary_slips_for_employees,
		submit_salary_slips_for_employees,
	)

	frappe.db.set_value("Account", f"Payroll Payable - {ABBR}", "account_type", "Payable")
	bank = frappe.db.get_value("Company", COMPANY, "default_bank_account")
	for months_back in (2, 1):
		start = get_first_day(add_months(TODAY, -months_back))
		end = get_last_day(start)
		if frappe.db.exists("Payroll Entry", {"start_date": start, "company": COMPANY, "docstatus": 1}):
			continue
		pe = frappe.get_doc(
			{
				"doctype": "Payroll Entry",
				"company": COMPANY,
				"posting_date": end,
				"payroll_frequency": "Monthly",
				"start_date": start,
				"end_date": end,
				"currency": "INR",
				"exchange_rate": 1,
				"payroll_payable_account": f"Payroll Payable - {ABBR}",
				"cost_center": f"Main - {ABBR}",
				"payment_account": bank,
			}
		)
		pe.insert(ignore_permissions=True)
		pe.fill_employee_details()
		pe.save(ignore_permissions=True)
		pe.create_salary_slips = lambda: None  # we create them synchronously below
		pe.submit()
		frappe.db.commit()
		employees = [r.employee for r in pe.employees]
		args = frappe._dict(
			salary_slip_based_on_timesheet=0,
			payroll_frequency="Monthly",
			start_date=start,
			end_date=end,
			company=COMPANY,
			posting_date=end,
			deduct_tax_for_unsubmitted_tax_exemption_proof=0,
			payroll_entry=pe.name,
			exchange_rate=1,
			currency="INR",
		)
		create_salary_slips_for_employees(employees, args, publish_progress=False)
		if not frappe.db.count("Salary Slip", {"payroll_entry": pe.name}):
			err = frappe.get_all("Error Log", fields=["error"], order_by="creation desc", limit=1)
			raise Exception("Salary slips were not created: " + (err[0].error[-1500:] if err else "unknown"))
		pe.reload()
		if months_back == 2:  # older month fully processed; latest month left as draft slips for review
			slips = pe.get_sal_slip_list(ss_status=0)
			frappe.db.set_single_value("Payroll Settings", "email_salary_slip_to_employee", 0)
			submit_salary_slips_for_employees(pe, slips, publish_progress=False)
			if frappe.db.count("Salary Slip", {"payroll_entry": pe.name, "docstatus": 0}):
				err = frappe.get_all("Error Log", fields=["error"], order_by="creation desc", limit=1)
				raise Exception(
					"Salary slips were not submitted: " + (err[0].error[-1500:] if err else "unknown")
				)
		frappe.db.commit()


# =============================================================== 6. expenses & travel
def expenses():
	accounts = {
		"Travel": "Travel Expenses",
		"Food": "Entertainment Expenses",
		"Calls": "Telephone Expenses",
		"Medical": "Miscellaneous Expenses",
		"Others": "Miscellaneous Expenses",
		"Conference & Events": "Marketing Expenses",
		"Internet / WFH": "Telephone Expenses",
		"Cloud & Software": "Administrative Expenses",
	}
	for etype, acc in accounts.items():
		if not frappe.db.exists("Expense Claim Type", etype):
			frappe.get_doc({"doctype": "Expense Claim Type", "expense_type": etype}).insert(
				ignore_permissions=True
			)
		t = frappe.get_doc("Expense Claim Type", etype)
		if not any(a.company == COMPANY for a in t.accounts):
			t.append("accounts", {"company": COMPANY, "default_account": f"{acc} - {ABBR}"})
			t.save(ignore_permissions=True)

	claims = [
		# key, days ago, [(type, amount, description)], approval, submit
		(
			"aisha",
			20,
			[
				("Conference & Events", 18500, "Booth materials - Bengaluru Web3 meetup"),
				("Travel", 6400, "Flights BOM-BLR"),
			],
			"Approved",
			True,
		),
		(
			"ananya",
			14,
			[
				("Travel", 12800, "Delhi - FIU-IND compliance workshop"),
				("Food", 2100, "Team dinner with auditors"),
			],
			"Approved",
			True,
		),
		("imran", 10, [("Cloud & Software", 9800, "Hardware security keys (x10)")], "Approved", True),
		("sneha", 7, [("Internet / WFH", 1499, "Monthly broadband")], "Approved", True),
		("siddharth", 5, [("Food", 3200, "Night desk meals during volatility week")], "Draft", False),
		("rohan", 3, [("Medical", 2400, "Vaccination"), ("Travel", 950, "Cab to hospital")], "Draft", False),
		(
			"yash",
			12,
			[("Conference & Events", 45000, "Sponsored creator event - no prior approval")],
			"Rejected",
			True,
		),
	]
	for key, ago, items, approval, submit in claims:
		e = emp_id(key)
		if frappe.db.exists("Expense Claim", {"employee": e, "posting_date": add_days(TODAY, -ago)}):
			continue
		ec = frappe.get_doc(
			{
				"doctype": "Expense Claim",
				"employee": e,
				"company": COMPANY,
				"currency": "INR",
				"exchange_rate": 1,
				"posting_date": add_days(TODAY, -ago),
				"approval_status": approval if submit else "Draft",
				"expense_approver": frappe.db.get_value("Employee", e, "expense_approver"),
				"payable_account": frappe.db.get_value(
					"Company", COMPANY, "default_expense_claim_payable_account"
				),
				"cost_center": f"Main - {ABBR}",
				"expenses": [
					{
						"expense_date": add_days(TODAY, -ago - 2),
						"expense_type": t,
						"amount": a,
						"sanctioned_amount": a if approval == "Approved" else 0,
						"description": desc,
						"cost_center": f"Main - {ABBR}",
					}
					for t, a, desc in items
				],
			}
		)
		ec.insert(ignore_permissions=True)
		if submit:
			ec.submit()

	frappe.db.set_value(
		"Account",
		frappe.db.get_value("Company", COMPANY, "default_employee_advance_account"),
		"account_type",
		"Receivable",
	)
	for key, amount, purpose in (
		("siddharth", 15000, "Travel advance - liquidity partner visit, Singapore"),
		("karan", 5000, "Advance for night-shift cab passes"),
	):
		e = emp_id(key)
		if frappe.db.exists("Employee Advance", {"employee": e}):
			continue
		adv = frappe.get_doc(
			{
				"doctype": "Employee Advance",
				"employee": e,
				"company": COMPANY,
				"currency": "INR",
				"exchange_rate": 1,
				"posting_date": add_days(TODAY, -9),
				"purpose": purpose,
				"advance_amount": amount,
				"advance_account": frappe.db.get_value(
					"Company", COMPANY, "default_employee_advance_account"
				),
			}
		)
		adv.insert(ignore_permissions=True)
		adv.submit()

	for p in ("Industry Conference", "Partner Meeting", "Regulatory Meeting"):
		get_or_insert({"doctype": "Purpose of Travel", "purpose_of_travel": p}, {"name": p})
	travels = [
		(
			"siddharth",
			"International",
			"Partner Meeting",
			"Bengaluru",
			"Singapore",
			12,
			"Quarterly review with the market maker",
		),
		(
			"ananya",
			"Domestic",
			"Regulatory Meeting",
			"Mumbai",
			"New Delhi",
			18,
			"FIU-IND reporting entity outreach session",
		),
		(
			"aisha",
			"Domestic",
			"Industry Conference",
			"Mumbai",
			"Bengaluru",
			25,
			"Speaking slot at a fintech summit",
		),
	]
	for key, ttype, purpose, frm, to, ahead, desc in travels:
		e = emp_id(key)
		if frappe.db.exists("Travel Request", {"employee": e}):
			continue
		dep = datetime.combine(add_days(TODAY, ahead), datetime.min.time()) + timedelta(hours=8)
		tr = frappe.get_doc(
			{
				"doctype": "Travel Request",
				"employee": e,
				"travel_type": ttype,
				"purpose_of_travel": purpose,
				"description": desc,
				"travel_funding": "Fully Sponsored",
				"itinerary": [
					{
						"travel_from": frm,
						"travel_to": to,
						"mode_of_travel": "Flight",
						"departure_date": dep,
						"arrival_date": dep + timedelta(hours=3),
						"lodging_required": 1,
						"meal_preference": "Vegetarian",
					}
				],
			}
		)
		tr.insert(ignore_permissions=True)
		if ahead < 20:
			tr.submit()


# =============================================================== 7. recruitment
def recruitment():
	swati_user = user_of("swati") or "Administrator"
	arjun_user = user_of("arjun") or "Administrator"
	cur_start, cur_end = fiscal_year_dates()

	for sk in (
		"Rust / Go",
		"Distributed Systems",
		"Matching Engine Design",
		"PMLA & FIU-IND Reporting",
		"Transaction Monitoring",
		"Customer Empathy",
		"Hindi & English Communication",
		"Market Microstructure",
	):
		get_or_insert({"doctype": "Skill", "skill_name": sk}, {"name": sk})

	if not frappe.db.exists("Staffing Plan", {"company": COMPANY, "docstatus": 1}):
		sp = frappe.get_doc(
			{
				"doctype": "Staffing Plan",
				"name": f"Hiring Plan FY {fy_label(cur_start)}",
				"__newname": f"Hiring Plan FY {fy_label(cur_start)}",
				"company": COMPANY,
				"department": dept("Engineering"),
				"from_date": cur_start,
				"to_date": cur_end,
				"staffing_details": [
					{
						"designation": "Senior Backend Engineer",
						"vacancies": 2,
						"estimated_cost_per_position": 4200000,
					},
					{
						"designation": "Security Engineer",
						"vacancies": 1,
						"estimated_cost_per_position": 3600000,
					},
				],
			}
		)
		sp.insert(ignore_permissions=True)
		sp.submit()

	reqs = [
		(
			"Senior Backend Engineer",
			"Engineering",
			2,
			4200000,
			"arjun",
			"Scale the matching engine and futures risk engine.",
		),
		(
			"AML Analyst",
			"Compliance & AML",
			1,
			1500000,
			"ananya",
			"Rising STR volumes after the futures launch.",
		),
		("Support Associate", "Customer Support", 3, 660000, "neeraj", "Extend Hindi support to 24x7."),
	]
	for desig, d, n, comp, by, why in reqs:
		if not frappe.db.exists("Job Requisition", {"designation": desig}):
			frappe.get_doc(
				{
					"doctype": "Job Requisition",
					"designation": desig,
					"department": dept(d),
					"no_of_positions": n,
					"expected_compensation": comp,
					"company": COMPANY,
					"status": "Open & Approved",
					"requested_by": emp_id(by),
					"posting_date": add_days(TODAY, -40),
					"reason_for_requesting": why,
					"description": f"<p>{why}</p>",
				}
			).insert(ignore_permissions=True)

	openings = [
		(
			"Senior Backend Engineer - Matching Engine",
			"Senior Backend Engineer",
			"Engineering",
			2,
			3500000,
			5000000,
			"Bengaluru HQ",
			"<p>Own the order-matching core of an FIU-IND registered exchange. Rust or Go, low-latency systems, strong testing habits.</p>",
		),
		(
			"AML Analyst",
			"AML Analyst",
			"Compliance & AML",
			1,
			1000000,
			1600000,
			"Mumbai Office",
			"<p>Investigate alerts, file STRs with FIU-IND and improve transaction-monitoring rules.</p>",
		),
		(
			"Customer Support Associate (Hindi / English)",
			"Support Associate",
			"Customer Support",
			3,
			450000,
			650000,
			"Bengaluru HQ",
			"<p>Help Indian traders 24x7 in Hindi and English. Rotating shifts.</p>",
		),
		(
			"Market Operations Analyst",
			"Market Operations Analyst",
			"Trading Operations",
			1,
			1200000,
			1800000,
			"Bengaluru HQ",
			"<p>Monitor order books, liquidity and market-maker health on a 24x7 desk.</p>",
		),
	]
	for title, desig, d, vac, lo, hi, branch, desc in openings:
		if frappe.db.exists("Job Opening", {"job_title": title}):
			continue
		frappe.get_doc(
			{
				"doctype": "Job Opening",
				"job_title": title,
				"designation": desig,
				"department": dept(d),
				"company": COMPANY,
				"status": "Open",
				"planned_vacancies": vac,
				"publish": 1,
				"publish_salary_range": 1,
				"lower_range": lo,
				"upper_range": hi,
				"currency": "INR",
				"salary_per": "Year",
				"location": branch,
				"employment_type": "Full-time",
				"description": desc,
				"posted_on": add_days(TODAY, -30),
				"closes_on": add_days(TODAY, 30),
			}
		).insert(ignore_permissions=True)

	def opening(title):
		return frappe.db.get_value("Job Opening", {"job_title": title})

	be, aml, sup = opening(openings[0][0]), opening(openings[1][0]), opening(openings[2][0])
	applicants = [
		("Aarav Sinha", be, "Shortlisted", "Website Listing", 0.8),
		("Nisha Varma", be, "Accepted", "Employee Referral", 1.0),
		("Kunal Bhatt", be, "Rejected", "Campaign", 0.4),
		("Rhea D'Souza", be, "Open", "Website Listing", 0.6),
		("Mohit Saini", aml, "Shortlisted", "Walk In", 0.8),
		("Tanvi Kulkarni", aml, "Replied", "Website Listing", 0.6),
		("Ayesha Khan", sup, "Accepted", "Campaign", 0.8),
		("Rajat Bhalla", sup, "Hold", "Website Listing", 0.6),
		("Pallavi Joshi", sup, "Open", "Employee Referral", 0.4),
		("Devika Menon", sup, "Rejected", "Walk In", 0.2),
	]
	for name, op, status, source, rating in applicants:
		email = name.lower().replace(" ", ".").replace("'", "") + "@candidates.example"
		if not frappe.db.exists("Job Applicant", {"email_id": email}):
			frappe.get_doc(
				{
					"doctype": "Job Applicant",
					"applicant_name": name,
					"email_id": email,
					"job_title": op,
					"status": status,
					"source": source,
					"applicant_rating": rating,
					"currency": "INR",
					"phone_number": f"+91 8{R.randint(100000000, 999999999)}",
				}
			).insert(ignore_permissions=True)

	def applicant(name):
		return frappe.db.get_value("Job Applicant", {"applicant_name": name})

	itypes = {
		"Technical Round": ["Rust / Go", "Distributed Systems", "Matching Engine Design"],
		"Compliance Case Study": ["PMLA & FIU-IND Reporting", "Transaction Monitoring"],
		"Support Role Play": ["Customer Empathy", "Hindi & English Communication"],
		"Culture & Values": ["Customer Empathy"],
	}
	for it, skills in itypes.items():
		if not frappe.db.exists("Interview Type", it):
			frappe.get_doc(
				{
					"doctype": "Interview Type",
					"interview_type_name": it,
					"description": f"{it} for Moon Exchange hiring",
					"expected_skill_set": [{"skill": s} for s in skills],
					"interviewers": [{"user": u} for u in {swati_user, arjun_user}],
				}
			).insert(ignore_permissions=True)

	interviews = [
		("Nisha Varma", "Technical Round", -12, "Cleared", arjun_user, 5),
		("Aarav Sinha", "Technical Round", 2, "Pending", arjun_user, None),
		("Kunal Bhatt", "Technical Round", -9, "Rejected", arjun_user, 2),
		("Mohit Saini", "Compliance Case Study", -4, "Under Review", swati_user, 4),
		("Ayesha Khan", "Support Role Play", -15, "Cleared", swati_user, 5),
		("Nisha Varma", "Culture & Values", -8, "Cleared", swati_user, 4),
	]
	for cand, itype, offset, status, interviewer, rating in interviews:
		ja = applicant(cand)
		if frappe.db.exists("Interview", {"job_applicant": ja, "interview_type": itype}):
			continue
		iv = frappe.get_doc(
			{
				"doctype": "Interview",
				"interview_type": itype,
				"job_applicant": ja,
				"scheduled_on": add_days(TODAY, offset),
				"from_time": "11:00:00",
				"to_time": "12:00:00",
				"status": "Pending",
				"interview_details": [{"interviewer": interviewer}],
			}
		)
		iv.insert(ignore_permissions=True)
		if rating:
			frappe.set_user(interviewer)
			fb = frappe.get_doc(
				{
					"doctype": "Interview Feedback",
					"interview": iv.name,
					"interview_type": itype,
					"interviewer": interviewer,
					"job_applicant": ja,
					"result": "Rejected" if status == "Rejected" else "Cleared",
					"feedback": "Strong fundamentals, clear communication."
					if status != "Rejected"
					else "Not a fit for the latency requirements.",
					"skill_assessment": [{"skill": s, "rating": rating / 5} for s in itypes[itype]],
				}
			)
			fb.insert(ignore_permissions=True)
			fb.submit()
			frappe.set_user("Administrator")
			iv.reload()
		if status in ("Cleared", "Rejected"):
			iv.status = status
			iv.submit()

	for term in ("Probation Period", "Notice Period", "Work Location", "Joining Bonus"):
		get_or_insert({"doctype": "Offer Term", "offer_term": term}, {"name": term})
	offers = [
		("Nisha Varma", "Senior Backend Engineer", "Accepted", 4400000),
		("Ayesha Khan", "Support Associate", "Awaiting Response", 600000),
	]
	for cand, desig, status, ctc in offers:
		ja = applicant(cand)
		if frappe.db.exists("Job Offer", {"job_applicant": ja}):
			continue
		jo = frappe.get_doc(
			{
				"doctype": "Job Offer",
				"job_applicant": ja,
				"applicant_name": cand,
				"applicant_email": frappe.db.get_value("Job Applicant", ja, "email_id"),
				"offer_date": add_days(TODAY, -6),
				"designation": desig,
				"company": COMPANY,
				"status": status,
				"offer_terms": [
					{"offer_term": "Probation Period", "value": "3 months"},
					{"offer_term": "Notice Period", "value": "60 days"},
					{"offer_term": "Work Location", "value": "Bengaluru HQ (hybrid)"},
					{"offer_term": "Joining Bonus", "value": f"INR {int(ctc * 0.05):,}"},
				],
			}
		)
		jo.insert(ignore_permissions=True)
		if status == "Accepted":
			jo.submit()

	if not frappe.db.exists("Appointment Letter Template", "Moon Exchange Standard"):
		frappe.get_doc(
			{
				"doctype": "Appointment Letter Template",
				"template_name": "Moon Exchange Standard",
				"introduction": "We are delighted to appoint you at Moon Exchange, an FIU-IND registered crypto exchange.",
				"terms": [
					{
						"title": "Confidentiality",
						"description": "You will keep customer, trading and compliance data confidential.",
					},
					{
						"title": "Trading Policy",
						"description": "Personal crypto trading follows the employee trading & pre-clearance policy.",
					},
					{"title": "Probation", "description": "The first three months are a probation period."},
				],
				"closing_notes": "Welcome to the team!",
			}
		).insert(ignore_permissions=True)
	ja = applicant("Nisha Varma")
	if not frappe.db.exists("Appointment Letter", {"job_applicant": ja}):
		tpl = frappe.get_doc("Appointment Letter Template", "Moon Exchange Standard")
		frappe.get_doc(
			{
				"doctype": "Appointment Letter",
				"job_applicant": ja,
				"applicant_name": "Nisha Varma",
				"company": COMPANY,
				"appointment_date": add_days(TODAY, 20),
				"appointment_letter_template": tpl.name,
				"introduction": tpl.introduction,
				"closing_notes": tpl.closing_notes,
				"terms": [{"title": t.title, "description": t.description} for t in tpl.terms],
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Employee Referral", {"email": "rhea.dsouza@candidates.example"}):
		ref = frappe.get_doc(
			{
				"doctype": "Employee Referral",
				"first_name": "Rhea",
				"last_name": "D'Souza",
				"email": "rhea.dsouza@candidates.example",
				"date": add_days(TODAY, -18),
				"status": "Pending",
				"for_designation": "Senior Backend Engineer",
				"referrer": emp_id("kavya"),
				"is_applicable_for_referral_bonus": 1,
				"referral_bonus_payment_status": "Unpaid",
			}
		)
		ref.insert(ignore_permissions=True)
		ref.submit()


# =============================================================== 8. employee lifecycle
def lifecycle():
	swati_user = user_of("swati") or "Administrator"
	if not frappe.db.exists("Employee Onboarding Template", {"title": "Engineering Onboarding"}):
		frappe.get_doc(
			{
				"doctype": "Employee Onboarding Template",
				"title": "Engineering Onboarding",
				"company": COMPANY,
				"department": dept("Engineering"),
				"activities": [
					{
						"activity_name": "Issue laptop, YubiKey and hardware wallet for testing",
						"user": swati_user,
						"begin_on": 0,
						"duration": 1,
					},
					{
						"activity_name": "Background verification & employee KYC",
						"role": "HR User",
						"begin_on": 0,
						"duration": 3,
					},
					{
						"activity_name": "Exchange security & phishing training",
						"user": swati_user,
						"begin_on": 1,
						"duration": 2,
					},
					{
						"activity_name": "PMLA / AML awareness module",
						"role": "HR User",
						"begin_on": 2,
						"duration": 2,
					},
					{
						"activity_name": "Production access (least privilege) approved by CTO",
						"user": swati_user,
						"begin_on": 5,
						"duration": 2,
					},
				],
			}
		).insert(ignore_permissions=True)
	ja = frappe.db.get_value("Job Applicant", {"applicant_name": "Nisha Varma"})
	jo = frappe.db.get_value("Job Offer", {"job_applicant": ja, "docstatus": 1})
	if jo and not frappe.db.exists("Employee Onboarding", {"job_applicant": ja}):
		tpl = frappe.get_doc("Employee Onboarding Template", {"title": "Engineering Onboarding"})
		ob = frappe.get_doc(
			{
				"doctype": "Employee Onboarding",
				"job_applicant": ja,
				"job_offer": jo,
				"employee_onboarding_template": tpl.name,
				"company": COMPANY,
				"employee_name": "Nisha Varma",
				"department": dept("Engineering"),
				"designation": "Senior Backend Engineer",
				"date_of_joining": add_days(TODAY, 20),
				"boarding_begins_on": add_days(TODAY, 20),
				"holiday_list": frappe.db.get_value("Company", COMPANY, "default_holiday_list"),
				"activities": [
					{k: a.get(k) for k in ("activity_name", "user", "role", "begin_on", "duration")}
					for a in tpl.activities
				],
			}
		)
		ob.insert(ignore_permissions=True)
		ob.submit()

	kavya = emp_id("kavya")
	if not frappe.db.exists("Employee Promotion", {"employee": kavya}):
		pr = frappe.get_doc(
			{
				"doctype": "Employee Promotion",
				"employee": kavya,
				"promotion_date": add_days(TODAY, -5),
				"current_ctc": 260000 * 12,
				"revised_ctc": 320000 * 12,
				"promotion_details": [
					{
						"property": "Designation",
						"fieldname": "designation",
						"current": "Backend Engineer",
						"new": "Senior Backend Engineer",
					}
				],
			}
		)
		pr.insert(ignore_permissions=True)
		pr.submit()

	gaurav = emp_id("gaurav")
	if not frappe.db.exists("Employee Transfer", {"employee": gaurav}):
		tr = frappe.get_doc(
			{
				"doctype": "Employee Transfer",
				"employee": gaurav,
				"transfer_date": add_days(TODAY, 10),
				"transfer_details": [
					{
						"property": "Branch",
						"fieldname": "branch",
						"current": "Mumbai Office",
						"new": "Bengaluru HQ",
					}
				],
			}
		)
		tr.insert(ignore_permissions=True)  # scheduled: submitted by HR on the transfer date

	manoj = emp_id(D.LEFT_EMPLOYEE[0])
	if not frappe.db.exists("Employee Separation Template", {"name": ["like", "%Standard Exit%"]}):
		frappe.get_doc(
			{
				"doctype": "Employee Separation Template",
				"title": "Standard Exit",
				"company": COMPANY,
				"activities": [
					{"activity_name": "Revoke exchange admin & VPN access", "user": swati_user},
					{"activity_name": "Collect laptop and security keys", "user": swati_user},
					{"activity_name": "Knowledge transfer to support lead", "role": "HR User"},
				],
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Employee Separation", {"employee": manoj}):
		tpl = frappe.db.get_value("Employee Separation Template", {"title": "Standard Exit"})
		acts = frappe.get_doc("Employee Separation Template", tpl).activities
		sep = frappe.get_doc(
			{
				"doctype": "Employee Separation",
				"employee": manoj,
				"company": COMPANY,
				"employee_separation_template": tpl,
				"boarding_begins_on": add_days(TODAY, -35),
				"resignation_letter_date": add_days(TODAY, -51),
				"exit_interview": "Relocating to Pune.",
				"activities": [{k: a.get(k) for k in ("activity_name", "user", "role")} for a in acts],
			}
		)
		sep.insert(ignore_permissions=True)
		sep.submit()
	if not frappe.db.exists("Exit Interview", {"employee": manoj}):
		ei = frappe.get_doc(
			{
				"doctype": "Exit Interview",
				"employee": manoj,
				"company": COMPANY,
				"status": "Completed",
				"date": add_days(TODAY, -22),
				"employee_status": "Exit Confirmed",
				"reference_document_name": None,
				"interview_summary": "<p>Relocating; would rejoin. Suggested better night-shift transport.</p>",
			}
		)
		ei.insert(ignore_permissions=True)
		ei.submit()
	if not frappe.db.exists("Full and Final Statement", {"employee": manoj}):
		frappe.get_doc(
			{
				"doctype": "Full and Final Statement",
				"employee": manoj,
				"transaction_date": add_days(TODAY, -15),
			}
		).insert(ignore_permissions=True)

	for gt in ("Workplace Conduct", "Shift Scheduling", "Payroll Query"):
		get_or_insert(
			{"doctype": "Grievance Type", "name": gt, "__newname": gt, "description": gt}, {"name": gt}
		)
	if not frappe.db.exists("Employee Grievance", {"raised_by": emp_id("karan")}):
		frappe.get_doc(
			{
				"doctype": "Employee Grievance",
				"subject": "Back-to-back night shifts",
				"raised_by": emp_id("karan"),
				"date": add_days(TODAY, -6),
				"status": "Open",
				"grievance_against_party": "Department",
				"grievance_against": dept("Trading Operations"),
				"grievance_type": "Shift Scheduling",
				"description": "Rostered on 3 night shifts after an evening shift without the 12 h rest gap.",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Employee Grievance", {"raised_by": emp_id("ritu")}):
		g = frappe.get_doc(
			{
				"doctype": "Employee Grievance",
				"subject": "Night allowance missing in payslip",
				"raised_by": emp_id("ritu"),
				"date": add_days(TODAY, -30),
				"status": "Resolved",
				"grievance_against_party": "Department",
				"grievance_against": dept("Accounts"),
				"grievance_type": "Payroll Query",
				"description": "Allowance for 4 night shifts not paid.",
				"resolved_by": swati_user,
				"resolution_date": add_days(TODAY, -26),
				"resolution_detail": "Paid as arrears in the next payroll.",
			}
		)
		g.insert(ignore_permissions=True)
		g.submit()


# =============================================================== 9. performance & training
def performance():
	kras = {
		"Platform Uptime (99.95%)": "Engineering",
		"Feature Delivery": "Engineering",
		"Security Posture": "Engineering",
		"STR Filing Timeliness": "Compliance",
		"KYC Turnaround Time": "Compliance",
		"Customer Satisfaction (CSAT)": "Support",
		"First Response Time": "Support",
		"Order Book Health": "Ops",
		"Incident Response": "Ops",
		"Team Collaboration": "All",
	}
	for k in kras:
		get_or_insert({"doctype": "KRA", "title": k}, {"name": k})
	for c in ("Ownership", "Communication", "Compliance Mindset", "Customer Focus"):
		get_or_insert({"doctype": "Employee Feedback Criteria", "criteria": c}, {"name": c})

	templates = {
		"Engineering Appraisal": [
			("Platform Uptime (99.95%)", 30),
			("Feature Delivery", 40),
			("Security Posture", 20),
			("Team Collaboration", 10),
		],
		"Compliance Appraisal": [
			("STR Filing Timeliness", 50),
			("KYC Turnaround Time", 40),
			("Team Collaboration", 10),
		],
		"Support & Ops Appraisal": [
			("Customer Satisfaction (CSAT)", 35),
			("First Response Time", 25),
			("Order Book Health", 20),
			("Incident Response", 20),
		],
	}
	for t, goals in templates.items():
		if not frappe.db.exists("Appraisal Template", t):
			frappe.get_doc(
				{
					"doctype": "Appraisal Template",
					"template_title": t,
					"goals": [{"key_result_area": k, "per_weightage": w} for k, w in goals],
					"rating_criteria": [
						{"criteria": c, "per_weightage": 25}
						for c in ("Ownership", "Communication", "Compliance Mindset", "Customer Focus")
					],
				}
			).insert(ignore_permissions=True)

	tmpl_for = {
		"Engineering": "Engineering Appraisal",
		"Product": "Engineering Appraisal",
		"Compliance & AML": "Compliance Appraisal",
		"Customer Support": "Support & Ops Appraisal",
		"Trading Operations": "Support & Ops Appraisal",
	}
	cur_start, cur_end = fiscal_year_dates()
	h2_start = getdate(cur_start).replace(month=10, day=1)
	cycle_start, cycle_end = (
		(h2_start, getdate(cur_end)) if TODAY >= h2_start else (getdate(cur_start), add_days(h2_start, -1))
	)
	cycle_name = f"{'H2' if TODAY >= h2_start else 'H1'} FY {fy_label(cur_start)}"
	if not frappe.db.exists("Appraisal Cycle", cycle_name):
		appraisees = []
		for s in staff():
			t = tmpl_for.get(s.row[4])
			if t and s.row[6] != "Intern":
				appraisees.append({"employee": s.name, "appraisal_template": t})
		cyc = frappe.get_doc(
			{
				"doctype": "Appraisal Cycle",
				"cycle_name": cycle_name,
				"company": COMPANY,
				"start_date": cycle_start,
				"end_date": cycle_end,
				"kra_evaluation_method": "Automated Based on Goal Progress",
				"status": "Not Started",
				"appraisees": appraisees,
				"description": "Half-yearly review. Goals roll up automatically from goal progress.",
			}
		)
		cyc.insert(ignore_permissions=True)
		cyc.status = "In Progress"
		cyc.save(ignore_permissions=True)
		cyc.create_appraisals()
		frappe.db.commit()

	goals = [
		("kavya", "Platform Uptime (99.95%)", "Matching engine p99 latency under 5 ms", 70),
		("kavya", "Feature Delivery", "Ship futures liquidation engine v2", 55),
		("rohan", "Feature Delivery", "INR withdrawal batching", 80),
		("imran", "Security Posture", "Hardware-key MFA for all admin accounts", 90),
		("vikram", "STR Filing Timeliness", "File every STR within 7 days", 65),
		("nidhi", "KYC Turnaround Time", "Median KYC approval under 10 minutes", 45),
		("ritu", "Customer Satisfaction (CSAT)", "CSAT 4.6+ on Hindi tickets", 60),
		("siddharth", "Order Book Health", "Top-10 pairs spread under 15 bps", 75),
	]
	for key, kra, title, progress in goals:
		e = emp_id(key)
		if frappe.db.exists("Goal", {"employee": e, "goal_name": title}):
			continue
		g = frappe.get_doc(
			{
				"doctype": "Goal",
				"goal_name": title,
				"employee": e,
				"kra": kra,
				"appraisal_cycle": cycle_name,
				"start_date": cycle_start,
				"end_date": cycle_end,
				"progress": progress,
				"status": "In Progress",
			}
		)
		g.insert(ignore_permissions=True)

	# 360 feedback from the manager
	appraisal = frappe.db.get_value("Appraisal", {"employee": emp_id("kavya"), "appraisal_cycle": cycle_name})
	if appraisal and not frappe.db.exists("Employee Performance Feedback", {"appraisal": appraisal}):
		epf = frappe.get_doc(
			{
				"doctype": "Employee Performance Feedback",
				"employee": emp_id("kavya"),
				"company": COMPANY,
				"reviewer": emp_id("arjun"),
				"added_on": now_datetime(),
				"appraisal": appraisal,
				"appraisal_cycle": cycle_name,
				"feedback": "<p>Owned the latency work end-to-end and mentors the interns well.</p>",
				"feedback_ratings": [
					{"criteria": c, "per_weightage": 25, "rating": r}
					for c, r in (
						("Ownership", 0.9),
						("Communication", 0.8),
						("Compliance Mindset", 0.8),
						("Customer Focus", 0.7),
					)
				],
			}
		)
		epf.insert(ignore_permissions=True)
		epf.submit()


def training():
	programs = [
		(
			"PMLA & FIU-IND Reporting Essentials",
			"Mandatory annual AML training for all staff of a reporting entity.",
		),
		(
			"Crypto Security & Phishing Awareness",
			"Social engineering, wallet drainer scams and secure key handling.",
		),
		("Handling Volatile Markets", "Desk playbook for circuit breakers, liquidations and customer comms."),
	]
	for name, desc in programs:
		get_or_insert(
			{
				"doctype": "Training Program",
				"training_program": name,
				"company": COMPANY,
				"description": f"<p>{desc}</p>",
				"trainer_name": "Ananya Bose" if "PMLA" in name else "Imran Qureshi",
			},
			{"name": name},
		)

	everyone = [s.name for s in staff()]
	events = [
		("AML Refresher - Q3", "PMLA & FIU-IND Reporting Essentials", -20, "Completed", everyone[:18]),
		("Phishing Drill Debrief", "Crypto Security & Phishing Awareness", -8, "Completed", everyone[::2]),
		(
			"Volatility Desk Playbook",
			"Handling Volatile Markets",
			9,
			"Scheduled",
			[s.name for s in staff() if s.row[4] in ("Trading Operations", "Customer Support")],
		),
	]
	for ename, prog, offset, status, emps in events:
		if frappe.db.exists("Training Event", {"event_name": ename}):
			continue
		start = datetime.combine(add_days(TODAY, offset), datetime.min.time()) + timedelta(hours=15)
		ev = frappe.get_doc(
			{
				"doctype": "Training Event",
				"event_name": ename,
				"training_program": prog,
				"company": COMPANY,
				"event_status": status,
				"type": "Workshop",
				"level": "Beginner",
				"location": "Bengaluru HQ - Boardroom / Google Meet",
				"start_time": start,
				"end_time": start + timedelta(hours=2),
				"introduction": f"<p>{prog}</p>",
				"trainer_name": "Compliance Team",
				"employees": [
					{
						"employee": e,
						"status": "Completed" if status == "Completed" else "Open",
						"attendance": "Present" if status == "Completed" else "",
						"is_mandatory": 1,
					}
					for e in emps
				],
			}
		)
		ev.insert(ignore_permissions=True)
		ev.submit()
		if status == "Completed":
			res = frappe.get_doc(
				{
					"doctype": "Training Result",
					"training_event": ev.name,
					"employees": [
						{"employee": e, "hours": 2, "grade": R.choice(["A", "A", "B", "B", "C"])}
						for e in emps
					],
				}
			)
			res.insert(ignore_permissions=True)
			res.submit()
			for e in emps[:3]:
				fb = frappe.get_doc(
					{
						"doctype": "Training Feedback",
						"employee": e,
						"training_event": ev.name,
						"feedback": R.choice(
							[
								"Very practical, loved the real STR examples.",
								"Good session; would like a follow-up on wallet screening.",
								"Clear and to the point.",
							]
						),
					}
				)
				fb.insert(ignore_permissions=True)
				fb.submit()


# =============================================================== 10. CRM (Twenty-style)
def crm():
	owners = {k: user_of(k) for k in ("aisha", "swati", "arjun", "kavya")}
	for name, domain, industry, rel, icp, size, vol, city, country, desc in D.CRM_COMPANIES:
		if frappe.db.exists("Pipeline Company", name):
			continue
		frappe.get_doc(
			{
				"doctype": "Pipeline Company",
				"company_name": name,
				"domain": f"https://{domain}",
				"industry": industry,
				"relationship": rel,
				"ideal_customer_profile": icp,
				"employees": size,
				"annual_volume": vol,
				"city": city,
				"country": country,
				"description": f"<p>{desc}</p>",
				"account_owner": owners["aisha"] if rel == "Prospect" else owners["swati"],
				"linkedin": f"https://www.linkedin.com/company/{domain.split('.')[0]}",
			}
		).insert(ignore_permissions=True)

	people = {}
	for first, last, company, title, city in D.CRM_PEOPLE:
		existing = frappe.db.get_value("Pipeline Person", {"first_name": first, "last_name": last})
		if not existing:
			domain = frappe.db.get_value("Pipeline Company", company, "domain").replace("https://", "")
			existing = (
				frappe.get_doc(
					{
						"doctype": "Pipeline Person",
						"first_name": first,
						"last_name": last,
						"company": company,
						"job_title": title,
						"city": city,
						"email": f"{first.lower()}@{domain}",
						"phone": f"+91 7{R.randint(100000000, 999999999)}",
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		people[(company, first)] = existing

	opps = {}
	for name, company, contact, product, source, stage, amount, close, owner in D.CRM_OPPORTUNITIES:
		existing = frappe.db.get_value("Pipeline Opportunity", {"opportunity_name": name})
		if not existing:
			existing = (
				frappe.get_doc(
					{
						"doctype": "Pipeline Opportunity",
						"opportunity_name": name,
						"company": company,
						"point_of_contact": people.get((company, contact)),
						"product": product,
						"source": source,
						"stage": stage,
						"amount": amount,
						"close_date": add_days(TODAY, close),
						"opportunity_owner": owners.get(owner),
						"lost_reason": "Bank policy blocks automated sweeps to VDA platforms."
						if stage == "Lost"
						else None,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		opps[name] = existing

	for title, status, prio, due, who, company, opp in D.CRM_TASKS:
		if frappe.db.exists("Pipeline Task", {"title": title}):
			continue
		frappe.get_doc(
			{
				"doctype": "Pipeline Task",
				"title": title,
				"status": status,
				"priority": prio,
				"due_date": add_days(TODAY, due),
				"assignee": owners.get(who) or owners["swati"],
				"company": company,
				"opportunity": opps.get(opp),
			}
		).insert(ignore_permissions=True)

	for title, company, opp, body in D.CRM_NOTES:
		if frappe.db.exists("Pipeline Note", {"title": title}):
			continue
		frappe.get_doc(
			{
				"doctype": "Pipeline Note",
				"title": title,
				"company": company,
				"opportunity": opps.get(opp),
				"body": body,
			}
		).insert(ignore_permissions=True)

	# Twenty-style workflow automation: notify the owner when a deal is won
	if not frappe.db.exists("Notification", "Pipeline - Deal Won"):
		frappe.get_doc(
			{
				"doctype": "Notification",
				"name": "Pipeline - Deal Won",
				"__newname": "Pipeline - Deal Won",
				"subject": "Deal won: {{ doc.opportunity_name }}",
				"document_type": "Pipeline Opportunity",
				"event": "Value Change",
				"value_changed": "stage",
				"condition": "doc.stage == 'Customer'",
				"channel": "System Notification",
				"enabled": 1,
				"send_system_notification": 1,
				"message": "{{ doc.company }} is now a customer ({{ frappe.format(doc.amount, {'fieldtype': 'Currency', 'options': 'INR'}) }}).",
				"recipients": [{"receiver_by_document_field": "opportunity_owner"}],
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Notification", "Pipeline - Task Assigned"):
		frappe.get_doc(
			{
				"doctype": "Notification",
				"name": "Pipeline - Task Assigned",
				"__newname": "Pipeline - Task Assigned",
				"subject": "New CRM task: {{ doc.title }}",
				"document_type": "Pipeline Task",
				"event": "New",
				"channel": "System Notification",
				"enabled": 1,
				"message": "Due {{ doc.due_date }} for {{ doc.company or '' }}",
				"recipients": [{"receiver_by_document_field": "assignee"}],
			}
		).insert(ignore_permissions=True)


def finishing_touches():
	# geofenced mobile check-ins (Shift Location radius) from now on
	frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)
	# Make the HR workspace the landing page for the admin
	frappe.db.set_value("User", "Administrator", {"first_name": "Moon", "last_name": "Admin"})
	frappe.db.set_default("company", COMPANY)
	for u in frappe.get_all("User", filters={"name": ["like", f"%@{D.DEMO_DOMAIN}"]}, pluck="name"):
		frappe.defaults.set_user_default("company", COMPANY, u)
	frappe.clear_cache()


STEPS = [
	org_structure,
	fiscal_years_and_holidays,
	shifts_and_locations,
	users_and_employees,
	leave_setup,
	leave_applications,
	shift_assignments_and_requests,
	attendance_requests,
	checkins,
	auto_attendance,
	compensatory_leave,
	work_hours,
	payroll_setup,
	salary_structures,
	salary_assignments,
	additional_pay,
	payroll_runs,
	expenses,
	recruitment,
	lifecycle,
	performance,
	training,
	crm,
	finishing_touches,
]
