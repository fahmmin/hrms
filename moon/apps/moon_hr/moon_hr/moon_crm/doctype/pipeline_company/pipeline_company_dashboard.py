from frappe import _


def get_data():
	return {
		"fieldname": "company",
		"transactions": [
			{"label": _("People & Deals"), "items": ["Pipeline Person", "Pipeline Opportunity"]},
			{"label": _("Activity"), "items": ["Pipeline Task", "Pipeline Note"]},
		],
	}
