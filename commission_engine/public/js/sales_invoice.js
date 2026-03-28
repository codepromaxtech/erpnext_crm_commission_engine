// Commission Engine — Sales Invoice Integration
// Shows commission entries on Sales Invoice form + warns if no sales person tagged

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && !frm.doc.is_return) {
            frm.trigger("show_commission_info");
        }

        // Warning banner if no sales team
        if (!frm.doc.docstatus && !frm.doc.__islocal) {
            const sales_team = frm.doc.sales_team || [];
            if (!sales_team.length || !sales_team.some(r => r.sales_person)) {
                frm.dashboard.add_comment(
                    __("⚠️ No Sales Person assigned. Commission will NOT be calculated when this invoice is submitted. " +
                        "Add a Sales Person in the <b>Sales Team</b> section below."),
                    "orange",
                    true
                );
            }
        }
    },

    before_submit(frm) {
        // Warn before submission if no sales person
        const sales_team = frm.doc.sales_team || [];
        if (!sales_team.length || !sales_team.some(r => r.sales_person)) {
            frappe.validated = false;
            frappe.confirm(
                __("No Sales Person is assigned to this invoice. Commission entries will NOT be created.<br><br>" +
                    "Do you want to submit anyway?"),
                () => {
                    frappe.validated = true;
                    frm.save("Submit");
                }
            );
        }
    },

    show_commission_info(frm) {
        frappe.xcall("frappe.client.get_count", {
            doctype: "Commission Entry",
            filters: {
                sales_invoice: frm.doc.name,
                status: ["!=", "Cancelled"]
            }
        }).then(count => {
            if (count > 0) {
                // Fetch commission details
                frappe.xcall("frappe.client.get_list", {
                    doctype: "Commission Entry",
                    filters: { sales_invoice: frm.doc.name, status: ["!=", "Cancelled"] },
                    fields: ["name", "sales_person", "sales_person_name", "commission_amount",
                        "manager", "manager_name", "manager_commission_amount", "status", "commission_type"],
                    limit_page_length: 20
                }).then(entries => {
                    let total_sp = 0, total_mgr = 0;
                    let rows = "";
                    const currency = frappe.boot.sysdefaults.currency || "USD";

                    entries.forEach(e => {
                        const sp_amt = flt(e.commission_amount);
                        const mgr_amt = flt(e.manager_commission_amount);
                        total_sp += sp_amt;
                        total_mgr += mgr_amt;

                        const status_color = e.status === "Paid" ? "#36b37e" :
                            e.status === "Pending" ? "#f5a623" : "#de3618";
                        const type_color = e.commission_type === "One-Time" ? "#5e64ff" : "#29cd42";

                        rows += `
                        <tr>
                            <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                <a href="/app/commission-entry/${e.name}" style="font-weight:600;">${e.name}</a>
                            </td>
                            <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                ${e.sales_person_name || e.sales_person}
                            </td>
                            <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                ${e.manager_name || e.manager || "—"}
                            </td>
                            <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; text-align:right; font-weight:600;">
                                ${format_currency(sp_amt + mgr_amt, currency)}
                            </td>
                            <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                <span style="background:${type_color}; color:#fff; padding:2px 8px;
                                    border-radius:10px; font-size:10px; font-weight:600;">${e.commission_type}</span>
                            </td>
                            <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                <span style="background:${status_color}; color:#fff; padding:2px 8px;
                                    border-radius:10px; font-size:10px; font-weight:600;">${e.status}</span>
                            </td>
                        </tr>`;
                    });

                    const grand_total = total_sp + total_mgr;

                    const html = `
                    <div class="commission-invoice-summary" style="margin:12px 0;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
                            <span style="font-size:16px;">💰</span>
                            <span style="font-size:14px; font-weight:700; color:#2d3748;">
                                Commission Entries (${entries.length})
                            </span>
                            <span style="background:#5e64ff; color:#fff; padding:2px 10px;
                                border-radius:10px; font-size:12px; font-weight:600; margin-left:auto;">
                                Total: ${format_currency(grand_total, currency)}
                            </span>
                        </div>
                        <table style="width:100%; border-collapse:collapse; font-size:12px;">
                            <thead>
                                <tr style="background:#f8f9fc;">
                                    <th style="padding:8px 10px; text-align:left; font-weight:600; color:#6b7280;">Entry</th>
                                    <th style="padding:8px 10px; text-align:left; font-weight:600; color:#6b7280;">Salesperson</th>
                                    <th style="padding:8px 10px; text-align:left; font-weight:600; color:#6b7280;">Manager</th>
                                    <th style="padding:8px 10px; text-align:right; font-weight:600; color:#6b7280;">Commission</th>
                                    <th style="padding:8px 10px; text-align:left; font-weight:600; color:#6b7280;">Type</th>
                                    <th style="padding:8px 10px; text-align:left; font-weight:600; color:#6b7280;">Status</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>`;

                    // Insert after the dashboard
                    $(frm.fields_dict.items_section.$wrapper || frm.fields_dict.items_section.wrapper)
                        .find(".commission-invoice-summary").remove();
                    frm.dashboard.add_section(html, __("Commission"));
                });
            }
        });
    },
});
