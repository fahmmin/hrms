frappe.query_reports["Pipeline Summary"] = {
	filters: [
		{ fieldname: "opportunity_owner", label: __("Owner"), fieldtype: "Link", options: "User" },
		{ fieldname: "product", label: __("Product"), fieldtype: "Select", options: "\nSpot API\nFutures API\nOTC Desk\nInstitutional Custody\nToken Listing\nINR Payments\nCo-marketing" },
		{ fieldname: "from_date", label: __("Close From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("Close To"), fieldtype: "Date" },
	],
};
