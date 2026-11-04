// Copyright (c) 2026, Moon Exchange
frappe.ui.form.on("Work Hour Policy", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Recalculate last 30 days"), () => {
			frappe.call({
				method: "moon_hr.moon_hr.work_hours.recalculate",
				freeze: true,
				freeze_message: __("Recalculating work logs..."),
			}).then((r) => {
				const m = r.message || {};
				frappe.show_alert({
					message: m.queued
						? __("Queued for {0} employees", [m.employees])
						: __("Updated {0} day logs for {1} employees", [m.days, m.employees]),
					indicator: "green",
				});
			});
		});
		frm.add_custom_button(__("Employees on this policy"), () => {
			frm.call("get_employees").then((r) => {
				const rows = (r.message || [])
					.map((e) => `<tr><td>${e.name}</td><td>${frappe.utils.escape_html(e.employee_name)}</td><td>${e.employment_type || ""}</td><td>${e.moon_daily_hours_override || ""}</td></tr>`)
					.join("");
				frappe.msgprint({
					title: __("Employees on {0}", [frm.doc.name]),
					message: `<table class="table table-bordered"><tr><th>${__("ID")}</th><th>${__("Name")}</th><th>${__("Employment Type")}</th><th>${__("Personal hours/day")}</th></tr>${rows}</table>`,
					wide: true,
				});
			});
		});
	},
});
