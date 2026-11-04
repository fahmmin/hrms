frappe.ui.form.on("Pipeline Company", {
	refresh(frm) {
		if (frm.is_new()) return;
		const make = (doctype) => frappe.new_doc(doctype, { company: frm.doc.name });
		frm.add_custom_button(__("Person"), () => make("Pipeline Person"), __("Add"));
		frm.add_custom_button(__("Opportunity"), () => make("Pipeline Opportunity"), __("Add"));
		frm.add_custom_button(__("Task"), () => make("Pipeline Task"), __("Add"));
		frm.add_custom_button(__("Note"), () => make("Pipeline Note"), __("Add"));
		if (frm.doc.domain) {
			frm.add_custom_button(__("Open Website"), () => window.open(frm.doc.domain.startsWith("http") ? frm.doc.domain : `https://${frm.doc.domain}`));
		}
	},
});
