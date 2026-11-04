frappe.listview_settings["Pipeline Task"] = {
	add_fields: ["status", "due_date"],
	get_indicator(doc) {
		if (doc.status === "Done") return [__("Done"), "green", "status,=,Done"];
		if (doc.due_date && frappe.datetime.get_diff(doc.due_date, frappe.datetime.get_today()) < 0)
			return [__("Overdue"), "red", "status,!=,Done"];
		return [__(doc.status), doc.status === "In progress" ? "orange" : "gray", `status,=,${doc.status}`];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Task Board"), () => frappe.set_route("List", "Pipeline Task", "Kanban", "Tasks by Status"));
	},
};
