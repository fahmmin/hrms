// Copyright (c) 2026, Moon Exchange
frappe.query_reports["Employee Work Hours"] = {
	filters: [
		{ fieldname: "view", label: __("View"), fieldtype: "Select", options: "Summary\nDaily", default: "Summary" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -30), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldname: "employment_type", label: __("Employment Type"), fieldtype: "Link", options: "Employment Type" },
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "utilisation" && data.utilisation != null) {
			const color = data.utilisation >= 95 ? "green" : data.utilisation >= 80 ? "orange" : "red";
			return `<span style="color: var(--${color}-600); font-weight: 600">${value}</span>`;
		}
		if (column.fieldname === "status") {
			const color = { "On Track": "green", Overtime: "blue", Short: "orange", "Half Day": "orange", Absent: "red" }[data.status];
			if (color) return `<span class="indicator-pill ${color}">${value}</span>`;
		}
		return value;
	},
	onload(report) {
		report.page.add_inner_button(__("Recalculate"), () => {
			const f = report.get_values();
			frappe.call({
				method: "moon_hr.moon_hr.work_hours.recalculate",
				args: { from_date: f.from_date, to_date: f.to_date, employee: f.employee, company: f.company, department: f.department },
				freeze: true,
				freeze_message: __("Recalculating from check-ins..."),
			}).then(() => report.refresh());
		});
	},
};
