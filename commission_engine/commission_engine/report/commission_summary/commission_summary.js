// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.query_reports["Commission Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Month"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Month"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
        },
        {
            fieldname: "sales_person",
            label: __("Sales Person"),
            fieldtype: "Link",
            options: "Sales Person",
        },
        {
            fieldname: "manager",
            label: __("Manager"),
            fieldtype: "Link",
            options: "Sales Person",
        },
        {
            fieldname: "commission_type",
            label: __("Commission Type"),
            fieldtype: "Select",
            options: "\nOne-Time\nRecurring",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nPending\nPaid",
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
        },
    ],
};
