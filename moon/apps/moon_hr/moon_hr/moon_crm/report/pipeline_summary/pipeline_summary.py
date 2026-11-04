# Copyright (c) 2026, Moon Exchange
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

STAGES = ["New", "Screening", "Meeting", "Proposal", "Customer", "Lost"]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conds = {}
	if filters.opportunity_owner:
		conds["opportunity_owner"] = filters.opportunity_owner
	if filters.product:
		conds["product"] = filters.product
	if filters.from_date and filters.to_date:
		conds["close_date"] = ["between", [filters.from_date, filters.to_date]]

	opps = frappe.get_all(
		"Pipeline Opportunity", filters=conds, fields=["stage", "amount", "weighted_amount", "product"]
	)
	rows = []
	for stage in STAGES:
		items = [o for o in opps if o.stage == stage]
		rows.append(
			{
				"stage": stage,
				"count": len(items),
				"amount": sum(flt(o.amount) for o in items),
				"weighted_amount": sum(flt(o.weighted_amount) for o in items),
			}
		)
	columns = [
		{"label": _("Stage"), "fieldname": "stage", "fieldtype": "Data", "width": 140},
		{"label": _("Opportunities"), "fieldname": "count", "fieldtype": "Int", "width": 120},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "INR",
			"width": 160,
		},
		{
			"label": _("Weighted Amount"),
			"fieldname": "weighted_amount",
			"fieldtype": "Currency",
			"options": "INR",
			"width": 160,
		},
	]
	open_rows = [r for r in rows if r["stage"] not in ("Customer", "Lost")]
	chart = {
		"data": {
			"labels": [r["stage"] for r in open_rows],
			"datasets": [{"name": _("Pipeline (INR)"), "values": [r["amount"] for r in open_rows]}],
		},
		"type": "bar",
		"colors": ["#2490ef"],
	}
	won = next(r for r in rows if r["stage"] == "Customer")
	lost = next(r for r in rows if r["stage"] == "Lost")
	closed = won["count"] + lost["count"]
	summary = [
		{
			"value": sum(r["amount"] for r in open_rows),
			"label": _("Open Pipeline"),
			"datatype": "Currency",
			"currency": "INR",
			"indicator": "Blue",
		},
		{
			"value": sum(r["weighted_amount"] for r in open_rows),
			"label": _("Weighted Pipeline"),
			"datatype": "Currency",
			"currency": "INR",
		},
		{
			"value": won["amount"],
			"label": _("Won"),
			"datatype": "Currency",
			"currency": "INR",
			"indicator": "Green",
		},
		{
			"value": round(100 * won["count"] / closed, 1) if closed else 0,
			"label": _("Win Rate %"),
			"datatype": "Percent",
		},
	]
	return columns, rows, None, chart, summary
