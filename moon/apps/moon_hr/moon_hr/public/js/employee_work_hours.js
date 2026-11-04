// Work Hours banner on the Employee form (Moon Exchange)
frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (frm.is_new()) return;
		frappe.call({ method: "moon_hr.moon_hr.work_hours.get_my_hours", args: { employee: frm.doc.name } }).then((r) => {
			const m = r.message;
			if (!m || !m.policy) return;
			const wk = frm.doc.moon_hours_this_week || 0;
			const wkExp = frm.doc.moon_expected_this_week || 0;
			frm.dashboard.add_comment(
				__("Work hours: {0} h/day on <b>{1}</b> &middot; this week {2} / {3} h &middot; today {4} h {5}", [
					m.daily_hours, m.policy, wk, wkExp, m.today_worked, m.today_status ? `(${__(m.today_status)})` : "",
				]),
				wk + 0.25 >= wkExp ? "green" : "orange",
				true
			);
		});
		frm.add_custom_button(__("Work Logs"), () => frappe.set_route("List", "Employee Work Log", { employee: frm.doc.name }), __("View"));
		frm.add_custom_button(__("Work Hours Report"), () => frappe.set_route("query-report", "Employee Work Hours", { employee: frm.doc.name }), __("View"));
	},
});
