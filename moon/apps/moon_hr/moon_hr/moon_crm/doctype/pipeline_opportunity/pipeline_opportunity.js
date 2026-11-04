frappe.ui.form.on("Pipeline Opportunity", {
	refresh(frm) {
		if (frm.is_new()) return;
		const base = { company: frm.doc.company, opportunity: frm.doc.name, person: frm.doc.point_of_contact };
		frm.add_custom_button(__("Task"), () => frappe.new_doc("Pipeline Task", base), __("Add"));
		frm.add_custom_button(__("Note"), () => frappe.new_doc("Pipeline Note", base), __("Add"));
	},
	point_of_contact(frm) {
		if (frm.doc.point_of_contact && !frm.doc.company) {
			frappe.db.get_value("Pipeline Person", frm.doc.point_of_contact, "company").then((r) => frm.set_value("company", r.message.company));
		}
	},
	setup(frm) {
		frm.set_query("point_of_contact", () => ({ filters: frm.doc.company ? { company: frm.doc.company } : {} }));
	},
});
