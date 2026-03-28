// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Entry", {
    refresh(frm) {
        frm.trigger("set_status_indicator");
        frm.trigger("render_commission_dashboard");
        frm.trigger("setup_actions");

        // Timeline badge
        if (!frm.doc.__islocal && frm.doc.commission_type) {
            const badge_color = frm.doc.commission_type === "One-Time" ? "#5e64ff" : "#29cd42";
            frm.timeline.wrapper && frm.timeline.wrapper.prepend(`
                <div style="padding: 8px 15px; margin-bottom: 8px;">
                    <span style="background: ${badge_color}; color: #fff; padding: 3px 10px;
                        border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;">
                        ${frm.doc.commission_type} Commission
                    </span>
                </div>
            `);
        }
    },

    setup_actions(frm) {
        frm.page.clear_actions_menu();

        if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
            frm.add_custom_button(__("Mark as Paid"), () => {
                const base = flt(frm.doc.base_amount);
                const sp_amt = flt(frm.doc.commission_amount);
                const mgr_amt = flt(frm.doc.manager_commission_amount);
                const total = sp_amt + mgr_amt;
                const currency = frappe.boot.sysdefaults.currency || "USD";

                // Fetch commission settings for account info
                frappe.xcall("frappe.client.get", {
                    doctype: "Commission Settings",
                    name: "Commission Settings"
                }).then(settings => {
                    const expense_acct = settings.commission_expense_account || "Not configured";
                    const payable_acct = settings.commission_payable_account || "Not configured";
                    const auto_je = settings.auto_create_journal_entry ? "Yes" : "No";

                    let msg = `
                    <div style="padding:8px 0;">
                        <div style="font-size:13px; font-weight:700; color:#2d3748; margin-bottom:12px;">
                            📋 Payment Summary for ${frm.doc.name}
                        </div>

                        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-bottom:14px;">
                            <tr style="background:#f0f4ff;">
                                <td colspan="2" style="padding:8px 10px; font-weight:700; color:#5e64ff;">
                                    Invoice Details
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Sales Invoice</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">${frm.doc.sales_invoice}</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Customer</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">${frm.doc.customer_name || frm.doc.customer}</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Invoice Amount</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">${format_currency(base, currency)}</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Commission Type</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                    <span style="background:${frm.doc.commission_type === 'One-Time' ? '#5e64ff' : '#29cd42'};
                                        color:#fff; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600;">
                                        ${frm.doc.commission_type}
                                    </span>
                                </td>
                            </tr>
                        </table>

                        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-bottom:14px;">
                            <tr style="background:#e8f5e9;">
                                <td colspan="3" style="padding:8px 10px; font-weight:700; color:#2e7d32;">
                                    💰 Commission Payout
                                </td>
                            </tr>
                            <tr style="background:#f8f9fc;">
                                <td style="padding:6px 10px; font-weight:600; color:#6b7280;">Role</td>
                                <td style="padding:6px 10px; font-weight:600; color:#6b7280;">Person</td>
                                <td style="padding:6px 10px; font-weight:600; color:#6b7280; text-align:right;">Amount</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                    <span style="background:#5e64ff; color:#fff; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600;">Salesperson</span>
                                </td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">
                                    ${frm.doc.sales_person_name || frm.doc.sales_person}
                                </td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; text-align:right; font-weight:700; color:#5e64ff;">
                                    ${format_currency(sp_amt, currency)} <span style="color:#9ca3af; font-weight:400;">(${flt(frm.doc.commission_pct, 2)}%)</span>
                                </td>
                            </tr>`;

                    if (frm.doc.manager) {
                        msg += `
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0;">
                                    <span style="background:#f5a623; color:#fff; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600;">Manager</span>
                                </td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">
                                    ${frm.doc.manager_name || frm.doc.manager}
                                </td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; text-align:right; font-weight:700; color:#f5a623;">
                                    ${format_currency(mgr_amt, currency)} <span style="color:#9ca3af; font-weight:400;">(${flt(frm.doc.manager_commission_pct, 2)}%)</span>
                                </td>
                            </tr>`;
                    }

                    msg += `
                            <tr style="background:#e8f5e9;">
                                <td colspan="2" style="padding:8px 10px; font-weight:700; color:#2e7d32;">
                                    Total Payout
                                </td>
                                <td style="padding:8px 10px; text-align:right; font-weight:700; font-size:14px; color:#2e7d32;">
                                    ${format_currency(total, currency)}
                                </td>
                            </tr>
                        </table>`;

                    if (auto_je === "Yes") {
                        msg += `
                        <table style="width:100%; border-collapse:collapse; font-size:12px;">
                            <tr style="background:#fff3e0;">
                                <td colspan="2" style="padding:8px 10px; font-weight:700; color:#e65100;">
                                    📝 Journal Entry (Auto-Created)
                                </td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Debit Account</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">${expense_acct}</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Credit Account</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">${payable_acct}</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; color:#6b7280;">Posting Date</td>
                                <td style="padding:6px 10px; border-bottom:1px solid #f0f0f0; font-weight:600;">${frappe.datetime.nowdate()}</td>
                            </tr>
                            <tr>
                                <td style="padding:6px 10px; color:#6b7280;">Amount</td>
                                <td style="padding:6px 10px; font-weight:700; color:#e65100;">${format_currency(total, currency)}</td>
                            </tr>
                        </table>`;
                    }

                    msg += `</div>`;

                    frappe.confirm(
                        msg,
                        () => {
                            frm.set_value("status", "Paid");
                            frm.save().then(() => {
                                frappe.show_alert({
                                    message: __("Commission marked as Paid — Total: {0}", [format_currency(total, currency)]),
                                    indicator: "green"
                                });
                            });
                        },
                        () => { },
                        __("Confirm Commission Payment")
                    );
                });
            }, __("Actions"));

            frm.add_custom_button(__("Cancel Commission"), () => {
                frappe.confirm(
                    __("Cancel this commission entry? This cannot be undone."),
                    () => {
                        frm.set_value("status", "Cancelled");
                        frm.save().then(() => {
                            frappe.show_alert({
                                message: __("Commission Cancelled"),
                                indicator: "red"
                            });
                        });
                    }
                );
            }, __("Actions"));

            // Make the primary action stand out
            frm.page.btn_primary && frm.page.btn_primary.addClass("btn-primary-dark");
        }

        // Quick link to Journal Entry
        if (frm.doc.journal_entry) {
            frm.add_custom_button(__("View Journal Entry"), () => {
                frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
            }).addClass("btn-default");
        }
    },

    render_commission_dashboard(frm) {
        if (frm.doc.__islocal) return;

        const base = flt(frm.doc.base_amount);
        const sp_amt = flt(frm.doc.commission_amount);
        const mgr_amt = flt(frm.doc.manager_commission_amount);
        const total = sp_amt + mgr_amt;
        const currency = frappe.boot.sysdefaults.currency || "USD";

        const status_config = {
            "Pending": { color: "#f5a623", bg: "#fef3e0", icon: "⏳" },
            "Paid": { color: "#36b37e", bg: "#e6f9f0", icon: "✅" },
            "Cancelled": { color: "#de3618", bg: "#fce8e6", icon: "❌" },
        };
        const st = status_config[frm.doc.status] || status_config["Pending"];

        const section = frm.fields_dict.invoice_section;
        const wrapper = section.$wrapper || section.wrapper;

        // Remove any previous dashboard
        $(wrapper).find(".commission-dashboard").remove();

        const html = `
        <div class="commission-dashboard" style="margin: 10px 0 20px 0;">
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <!-- Base Amount -->
                <div style="flex: 1; min-width: 150px; background: #f8f9fc; border-radius: 10px;
                    padding: 16px; border-left: 4px solid #6c7ae0;">
                    <div style="font-size: 11px; color: #8d99ae; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 4px;">Invoice Amount</div>
                    <div style="font-size: 20px; font-weight: 700; color: #2d3748;">
                        ${format_currency(base, currency)}
                    </div>
                </div>

                <!-- Salesperson Commission -->
                <div style="flex: 1; min-width: 150px; background: #f0f4ff; border-radius: 10px;
                    padding: 16px; border-left: 4px solid #5e64ff;">
                    <div style="font-size: 11px; color: #8d99ae; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 4px;">
                        Salesperson (${flt(frm.doc.commission_pct, 2)}%)
                    </div>
                    <div style="font-size: 20px; font-weight: 700; color: #5e64ff;">
                        ${format_currency(sp_amt, currency)}
                    </div>
                    <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">
                        ${frm.doc.sales_person_name || frm.doc.sales_person || "—"}
                    </div>
                </div>

                <!-- Manager Commission -->
                <div style="flex: 1; min-width: 150px; background: ${frm.doc.manager ? '#f0fdf4' : '#f9fafb'}; border-radius: 10px;
                    padding: 16px; border-left: 4px solid ${frm.doc.manager ? '#29cd42' : '#d1d5db'};">
                    <div style="font-size: 11px; color: #8d99ae; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 4px;">
                        Manager (${flt(frm.doc.manager_commission_pct, 2)}%)
                    </div>
                    <div style="font-size: 20px; font-weight: 700; color: ${frm.doc.manager ? '#29cd42' : '#9ca3af'};">
                        ${frm.doc.manager ? format_currency(mgr_amt, currency) : "N/A"}
                    </div>
                    <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">
                        ${frm.doc.manager_name || frm.doc.manager || "No manager assigned"}
                    </div>
                </div>

                <!-- Total + Status -->
                <div style="flex: 1; min-width: 150px; background: ${st.bg}; border-radius: 10px;
                    padding: 16px; border-left: 4px solid ${st.color};">
                    <div style="font-size: 11px; color: #8d99ae; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 4px;">Total Commission</div>
                    <div style="font-size: 20px; font-weight: 700; color: ${st.color};">
                        ${format_currency(total, currency)}
                    </div>
                    <div style="font-size: 11px; margin-top: 2px;">
                        <span style="background: ${st.color}; color: #fff; padding: 2px 8px;
                            border-radius: 10px; font-weight: 600;">${st.icon} ${frm.doc.status}</span>
                    </div>
                </div>
            </div>
        </div>`;

        $(wrapper).prepend(html);
    },

    commission_pct(frm) {
        frm.trigger("calculate_amounts");
    },

    manager_commission_pct(frm) {
        frm.trigger("calculate_amounts");
    },

    base_amount(frm) {
        frm.trigger("calculate_amounts");
    },

    calculate_amounts(frm) {
        const base = flt(frm.doc.base_amount);
        frm.set_value("commission_amount", base * flt(frm.doc.commission_pct) / 100);
        frm.set_value("manager_commission_amount", base * flt(frm.doc.manager_commission_pct) / 100);
    },

    set_status_indicator(frm) {
        const colors = {
            "Pending": "orange",
            "Paid": "green",
            "Cancelled": "red",
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "gray");
    },
});
