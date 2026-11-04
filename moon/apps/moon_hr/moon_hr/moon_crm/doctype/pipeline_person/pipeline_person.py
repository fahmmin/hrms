# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt

from frappe.model.document import Document


class PipelinePerson(Document):
	def validate(self):
		self.full_name = " ".join(p for p in (self.first_name, self.last_name) if p)
