# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from moon_hr.moon_hr.work_hours import DAY_FIELDS


class WorkHourPolicy(Document):
	def validate(self):
		days = sum(cint(self.get(d)) for d in DAY_FIELDS)
		if not days:
			frappe.throw(_("Select at least one working day."))
		if flt(self.daily_hours) <= 0 or flt(self.daily_hours) > 24:
			frappe.throw(_("Expected hours per day must be between 0 and 24."))
		self.weekly_hours = flt(self.daily_hours) * days
		if not flt(self.overtime_after):
			self.overtime_after = self.daily_hours

		if self.employment_type:
			other = frappe.db.get_value(
				"Work Hour Policy", {"employment_type": self.employment_type, "name": ("!=", self.name)}
			)
			if other:
				frappe.throw(
					_("Employment Type {0} already uses policy {1}.").format(
						frappe.bold(self.employment_type), frappe.bold(other)
					)
				)

	def on_update(self):
		if self.is_default:
			frappe.db.sql("update `tabWork Hour Policy` set is_default=0 where name!=%s", self.name)
		frappe.clear_document_cache("Work Hour Policy", self.name)

	@frappe.whitelist()
	def get_employees(self):
		from moon_hr.moon_hr.work_hours import get_employee_policy

		rows = frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=[
				"name",
				"employee_name",
				"employment_type",
				"moon_work_hour_policy",
				"moon_daily_hours_override",
			],
		)
		return [r for r in rows if get_employee_policy(r).name == self.name]
