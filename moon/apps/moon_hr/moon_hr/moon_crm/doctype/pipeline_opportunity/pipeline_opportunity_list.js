frappe.listview_settings["Pipeline Opportunity"] = {
	add_fields: ["stage"],
	get_indicator(doc) {
		const map = { New: "gray", Screening: "blue", Meeting: "purple", Proposal: "orange", Customer: "green", Lost: "red" };
		return [__(doc.stage), map[doc.stage] || "gray", `stage,=,${doc.stage}`];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Pipeline Board"), () => frappe.set_route("List", "Pipeline Opportunity", "Kanban", "Opportunities by Stage"));
		listview.page.add_inner_button(__("Pipeline Report"), () => frappe.set_route("query-report", "Pipeline Summary"));
	},
};
