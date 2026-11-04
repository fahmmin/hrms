from frappe import _


def get_data():
	return {
		"fieldname": "opportunity",
		"transactions": [{"label": _("Activity"), "items": ["Pipeline Task", "Pipeline Note"]}],
	}
