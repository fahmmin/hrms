// Copyright (c) 2026, Moon Exchange
frappe.ui.form.on("Employee Work Log", {
	refresh(frm) {
		if (frm.is_new()) return;
		const color = { "On Track": "green", Overtime: "blue", Short: "orange", "Half Day": "orange", Absent: "red", "In Progress": "purple" }[frm.doc.status] || "gray";
		frm.dashboard.set_headline_alert(
			`<b>${frm.doc.worked_hours || 0} h</b> ${__("worked of")} <b>${frm.doc.expected_hours || 0} h</b> ${__("expected")}` +
				(frm.doc.late_by_minutes ? ` &middot; ${__("late by {0} min", [frm.doc.late_by_minutes])}` : ""),
			color
		);
		frm.add_custom_button(__("Recalculate from Check-ins"), () =>
			frm.call("recalculate").then(() => frm.reload_doc())
		);
		frm.add_custom_button(__("Check-ins"), () =>
			frappe.set_route("List", "Employee Checkin", { employee: frm.doc.employee })
		);
	},
});
