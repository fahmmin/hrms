from frappe import _


def get_data():
	return {
		"fieldname": "person",
		"non_standard_fieldnames": {"Pipeline Opportunity": "point_of_contact"},
		"transactions": [
			{"label": _("Deals"), "items": ["Pipeline Opportunity"]},
			{"label": _("Activity"), "items": ["Pipeline Task", "Pipeline Note"]},
		],
	}
