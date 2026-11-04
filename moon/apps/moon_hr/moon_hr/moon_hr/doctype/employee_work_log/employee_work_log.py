# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class EmployeeWorkLog(Document):
	def validate(self):
		if self.flags.from_engine:
			return
		if self.is_manual:
			# derive the figures from the manually entered hours
			from moon_hr.moon_hr.work_hours import compute_day, get_employee_policy, get_status

			auto = compute_day(self.employee, self.date)
			policy = get_employee_policy(self.employee)
			self.day_type = auto.day_type
			self.expected_hours = auto.expected_hours
			self.work_hour_policy = policy.name
			self.source = "Manual"
			worked = flt(self.worked_hours)
			self.shortfall_hours = max(0.0, flt(self.expected_hours) - worked)
			from moon_hr.moon_hr.work_hours import OVERTIME_MIN_HOURS

			ot = worked - max(flt(policy.overtime_after), flt(self.expected_hours))
			self.overtime_hours = ot if ot >= OVERTIME_MIN_HOURS else 0.0
			self.status = get_status(
				self.day_type, flt(self.expected_hours), worked, policy, False, self.date
			)
		elif not self.is_new():
			frappe.throw(_("Tick 'Manual Entry' to edit worked hours by hand, or use Recalculate."))

	def on_update(self):
		if not self.flags.from_engine:
			from moon_hr.moon_hr.work_hours import update_employee_summary

			update_employee_summary(self.employee)

	@frappe.whitelist()
	def recalculate(self):
		from moon_hr.moon_hr.work_hours import recalculate_employee

		self.db_set("is_manual", 0)
		recalculate_employee(self.employee, self.date, self.date)
