// Commission Engine — Customer form integration
// Auto-fills sales_team when a Customer is created from a Lead
// Shows full commission breakdown: Salesperson + Manager

frappe.ui.form.on("Customer", {
    onload(frm) {
        // Only for new (unsaved) customers created from a lead
        if (frm.doc.__islocal && frm.doc.lead_name && (!frm.doc.sales_team || frm.doc.sales_team.length === 0)) {
            frm.trigger("auto_fill_sales_team_from_lead");
        }
    },

    lead_name(frm) {
        // Also trigger when lead_name changes
        if (frm.doc.__islocal && frm.doc.lead_name && (!frm.doc.sales_team || frm.doc.sales_team.length === 0)) {
            frm.trigger("auto_fill_sales_team_from_lead");
        }
    },

    auto_fill_sales_team_from_lead(frm) {
        frappe.xcall(
            "commission_engine.customer_hooks.resolve_sales_person_from_lead",
            { lead_name: frm.doc.lead_name }
        ).then(result => {
            if (!result || !result.sales_person) return;

            // Add salesperson to sales_team
            let row = frm.add_child("sales_team");
            row.sales_person = result.sales_person;
            row.allocated_percentage = 100;
            row.allocated_amount = 0;
            row.commission_rate = result.commission_rate || 0;
            frm.refresh_field("sales_team");

            // Build info message with salesperson + manager breakdown
            let sp_rate = result.commission_rate || 0;
            let mgr_rate = result.manager_commission_rate || 0;
            let mgr_name = result.manager_name || result.manager;

            let msg = `<div style="line-height:1.8">
                <div style="font-weight:700; font-size:13px; margin-bottom:6px;">
                    💰 Commission Structure Auto-Assigned from Lead Owner
                </div>
                <table style="width:100%; font-size:12px; border-collapse:collapse;">
                    <tr style="background:#f0f4ff;">
                        <td style="padding:6px 10px; font-weight:600;">Role</td>
                        <td style="padding:6px 10px; font-weight:600;">Person</td>
                        <td style="padding:6px 10px; font-weight:600; text-align:right;">Commission %</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 10px;">
                            <span style="background:#5e64ff; color:#fff; padding:2px 8px; border-radius:10px; font-size:10px;">Salesperson</span>
                        </td>
                        <td style="padding:6px 10px; font-weight:600;">${result.sales_person}</td>
                        <td style="padding:6px 10px; text-align:right; font-weight:700; color:#5e64ff;">${sp_rate}%</td>
                    </tr>`;

            if (mgr_name) {
                msg += `
                    <tr style="background:#f8f9fc;">
                        <td style="padding:6px 10px;">
                            <span style="background:#f5a623; color:#fff; padding:2px 8px; border-radius:10px; font-size:10px;">Manager</span>
                        </td>
                        <td style="padding:6px 10px; font-weight:600;">${mgr_name}</td>
                        <td style="padding:6px 10px; text-align:right; font-weight:700; color:#f5a623;">${mgr_rate}%</td>
                    </tr>`;
            }

            msg += `</table>`;

            if (!mgr_name) {
                msg += `<div style="color:#9ca3af; font-size:11px; margin-top:4px;">
                    ℹ️ No manager found in Sales Person hierarchy. Only salesperson commission will apply.
                </div>`;
            } else {
                msg += `<div style="color:#6b7280; font-size:11px; margin-top:6px;">
                    ℹ️ Manager commission is auto-calculated when the Sales Invoice is submitted.
                    The manager does not need to be in the Sales Team table.
                </div>`;
            }

            msg += `</div>`;

            frappe.msgprint({
                title: __("Commission Auto-Assigned"),
                message: msg,
                indicator: "green",
                wide: true,
            });
        });
    },
});
