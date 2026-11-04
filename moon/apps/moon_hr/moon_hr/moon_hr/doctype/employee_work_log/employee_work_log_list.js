frappe.listview_settings["Employee Work Log"] = {
	add_fields: ["status", "worked_hours", "expected_hours"],
	get_indicator(doc) {
		const map = {
			"On Track": "green", Overtime: "blue", Short: "orange", "Half Day": "orange", Absent: "red",
			"In Progress": "purple", "On Leave": "cyan", Holiday: "gray", "Weekly Off": "gray",
		};
		return [__(doc.status || "Pending"), map[doc.status] || "gray", `status,=,${doc.status}`];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Recalculate last 30 days"), () => {
			frappe.call({ method: "moon_hr.moon_hr.work_hours.recalculate", freeze: true }).then(() => listview.refresh());
		});
		listview.page.add_inner_button(__("Work Hours Report"), () => frappe.set_route("query-report", "Employee Work Hours"));
	},
};
