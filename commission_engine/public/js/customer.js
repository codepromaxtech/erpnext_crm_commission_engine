// Commission Engine — Customer form integration
// Auto-fills sales_team when a Customer is created from a Lead

frappe.ui.form.on("Customer", {
    onload(frm) {
        // Only for new (unsaved) customers created from a lead
        if (frm.doc.__islocal && frm.doc.lead_name && (!frm.doc.sales_team || frm.doc.sales_team.length === 0)) {
            frm.trigger("auto_fill_sales_team_from_lead");
        }
    },

    lead_name(frm) {
        // Also trigger when lead_name changes (e.g., user manually sets it)
        if (frm.doc.__islocal && frm.doc.lead_name && (!frm.doc.sales_team || frm.doc.sales_team.length === 0)) {
            frm.trigger("auto_fill_sales_team_from_lead");
        }
    },

    auto_fill_sales_team_from_lead(frm) {
        frappe.xcall(
            "commission_engine.customer_hooks.resolve_sales_person_from_lead",
            { lead_name: frm.doc.lead_name }
        ).then(result => {
            if (result && result.sales_person) {
                let row = frm.add_child("sales_team");
                row.sales_person = result.sales_person;
                row.allocated_percentage = 100;
                row.allocated_amount = 0;
                row.commission_rate = result.commission_rate || 0;
                frm.refresh_field("sales_team");

                frappe.show_alert({
                    message: __("Sales Person <b>{0}</b> auto-assigned from Lead Owner with {1}% commission",
                        [result.sales_person, result.commission_rate || 0]),
                    indicator: "green"
                });
            }
        });
    },
});
