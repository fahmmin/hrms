# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

STAGE_PROBABILITY = {"New": 10, "Screening": 25, "Meeting": 40, "Proposal": 65, "Customer": 100, "Lost": 0}


class PipelineOpportunity(Document):
	def validate(self):
		if self.has_value_changed("stage") or not self.probability:
			self.probability = STAGE_PROBABILITY.get(self.stage, 0)
		self.weighted_amount = flt(self.amount) * flt(self.probability) / 100
		if self.point_of_contact:
			person_company = frappe.db.get_value("Pipeline Person", self.point_of_contact, "company")
			if person_company and person_company != self.company:
				frappe.throw(
					_("{0} works at {1}, not {2}.").format(
						self.point_of_contact, person_company, self.company
					)
				)

	def on_update(self):
		if self.has_value_changed("stage") and self.stage == "Customer":
			frappe.db.set_value("Pipeline Company", self.company, "relationship", "Customer")
