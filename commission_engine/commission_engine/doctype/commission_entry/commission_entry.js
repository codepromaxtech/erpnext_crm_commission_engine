// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Entry", {
    refresh(frm) {
        frm.trigger("set_status_indicator");
        frm.trigger("render_commission_dashboard");
        frm.trigger("setup_actions");

        // Role + Type + Status badges
        if (!frm.doc.__islocal) {
            const type_color = frm.doc.commission_type === "One-Time" ? "#5e64ff" : "#29cd42";
            const role_color = frm.doc.commission_role === "Manager" ? "#f5a623" : "#5e64ff";
            const badges = [];

            if (frm.doc.commission_role) {
                badges.push(`<span style="background:${role_color}; color:#fff; padding:3px 10px;
                    border-radius:12px; font-size:11px; font-weight:600; text-transform:uppercase;">
                    ${frm.doc.commission_role}</span>`);
            }
            badges.push(`<span style="background:${type_color}; color:#fff; padding:3px 10px;
                border-radius:12px; font-size:11px; font-weight:600; text-transform:uppercase;">
                ${frm.doc.commission_type}</span>`);

            if (frm.doc.original_entry) {
                badges.push(`<span style="background:#de3618; color:#fff; padding:3px 10px;
                    border-radius:12px; font-size:11px; font-weight:600;">↩ REVERSAL</span>`);
            }

            frm.timeline.wrapper && frm.timeline.wrapper.prepend(
                `<div style="padding:8px 15px; margin-bottom:8px; display:flex; gap:6px;">${badges.join("")}</div>`
            );
        }
    },

    setup_actions(frm) {
        frm.page.clear_actions_menu();

        if (frm.doc.__islocal) return;

        const currency = frappe.boot.sysdefaults.currency || "USD";
        const amount = flt(frm.doc.commission_amount);
        const role = frm.doc.commission_role || "Salesperson";
        const payee = frm.doc.sales_person_name || frm.doc.sales_person;

        // --- PENDING: Show Approve button ---
        if (frm.doc.status === "Pending") {
            frm.add_custom_button(__("Approve"), () => {
                frappe.confirm(
                    __("Approve {0} commission of {1} for <b>{2}</b>?",
                        [role, format_currency(amount, currency), payee]),
                    () => {
                        frm.set_value("status", "Approved");
                        frm.save().then(() => {
                            frappe.show_alert({
                                message: __("Commission Approved ✓"),
                                indicator: "blue"
                            });
                        });
                    }
                );
            }, __("Actions"));

            frm.add_custom_button(__("Cancel"), () => {
                frappe.confirm(__("Cancel this commission entry?"), () => {
                    frm.set_value("status", "Cancelled");
                    frm.save().then(() => {
                        frappe.show_alert({ message: __("Cancelled"), indicator: "red" });
                    });
                });
            }, __("Actions"));
        }

        // --- APPROVED: Show Mark as Paid ---
        if (frm.doc.status === "Approved") {
            frm.add_custom_button(__("Mark as Paid"), () => {
                frappe.xcall("frappe.client.get", {
                    doctype: "Commission Settings",
                    name: "Commission Settings"
                }).then(settings => {
                    const expense_acct = settings.commission_expense_account || "Not set";
                    const payable_acct = settings.commission_payable_account || "Not set";
                    const auto_je = settings.auto_create_journal_entry;

                    let msg = `
                    <div style="padding:8px 0;">
                        <div style="font-size:13px; font-weight:700; color:#2d3748; margin-bottom:10px;">
                            💰 Payment: ${frm.doc.name}
                        </div>
                        <table style="width:100%; border-collapse:collapse; font-size:12px;">
                            <tr style="background:#f0f4ff;">
                                <td style="padding:6px 10px; color:#6b7280;">Payee</td>
                                <td style="padding:6px 10px; font-weight:600;">${payee}</td>
                            </tr>
                            <tr><td style="padding:6px 10px; color:#6b7280;">Role</td>
                                <td style="padding:6px 10px;">
                                    <span style="background:${role === 'Manager' ? '#f5a623' : '#5e64ff'};
                                        color:#fff; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600;">${role}</span>
                                </td>
                            </tr>
                            <tr style="background:#f0f4ff;">
                                <td style="padding:6px 10px; color:#6b7280;">Invoice</td>
                                <td style="padding:6px 10px; font-weight:600;">${frm.doc.sales_invoice}</td>
                            </tr>
                            <tr><td style="padding:6px 10px; color:#6b7280;">Rate</td>
                                <td style="padding:6px 10px;">${flt(frm.doc.commission_pct, 2)}%</td>
                            </tr>
                            <tr style="background:#e8f5e9;">
                                <td style="padding:8px 10px; font-weight:700; color:#2e7d32;">Amount</td>
                                <td style="padding:8px 10px; font-weight:700; font-size:14px; color:#2e7d32;">
                                    ${format_currency(amount, currency)}
                                </td>
                            </tr>`;

                    if (auto_je) {
                        msg += `
                            <tr style="background:#fff3e0;">
                                <td style="padding:6px 10px; color:#e65100; font-weight:600;">JE Debit</td>
                                <td style="padding:6px 10px; font-weight:600;">${expense_acct}</td>
                            </tr>
                            <tr style="background:#fff3e0;">
                                <td style="padding:6px 10px; color:#e65100; font-weight:600;">JE Credit</td>
                                <td style="padding:6px 10px; font-weight:600;">${payable_acct}</td>
                            </tr>`;
                    }
                    msg += `</table></div>`;

                    frappe.confirm(
                        msg,
                        () => {
                            frm.set_value("status", "Paid");
                            frm.save().then(() => {
                                frappe.show_alert({
                                    message: __("{0} paid to {1}: {2}",
                                        [role, payee, format_currency(amount, currency)]),
                                    indicator: "green"
                                });
                            });
                        },
                        () => { },
                        __("Confirm Payment")
                    );
                });
            }, __("Actions"));

            // Also allow cancel from Approved
            frm.add_custom_button(__("Cancel"), () => {
                frappe.confirm(__("Cancel this approved commission?"), () => {
                    frm.set_value("status", "Cancelled");
                    frm.save().then(() => {
                        frappe.show_alert({ message: __("Cancelled"), indicator: "red" });
                    });
                });
            }, __("Actions"));
        }

        // --- PENDING (no approval) : Direct Mark as Paid ---
        // Check if approval workflow is disabled — allow direct Pending → Paid
        if (frm.doc.status === "Pending") {
            frappe.xcall("frappe.client.get", {
                doctype: "Commission Settings",
                name: "Commission Settings"
            }).then(settings => {
                if (!settings.enable_approval_workflow) {
                    // Add direct "Mark as Paid" for non-approval mode
                    frm.add_custom_button(__("Mark as Paid (Direct)"), () => {
                        frappe.confirm(
                            __("Pay {0} commission of {1} to <b>{2}</b>? (No approval required)",
                                [role, format_currency(amount, currency), payee]),
                            () => {
                                frm.set_value("status", "Paid");
                                frm.save().then(() => {
                                    frappe.show_alert({
                                        message: __("Paid ✓"),
                                        indicator: "green"
                                    });
                                });
                            }
                        );
                    }, __("Actions"));
                }
            });
        }

        // View JE link
        if (frm.doc.journal_entry) {
            frm.add_custom_button(__("View Journal Entry"), () => {
                frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry);
            }).addClass("btn-default");
        }

        // View original/reversal entry
        if (frm.doc.original_entry) {
            frm.add_custom_button(__("View Original Entry"), () => {
                frappe.set_route("Form", "Commission Entry", frm.doc.original_entry);
            }).addClass("btn-default");
        }
        if (frm.doc.reversed_entry) {
            frm.add_custom_button(__("View Reversal Entry"), () => {
                frappe.set_route("Form", "Commission Entry", frm.doc.reversed_entry);
            }).addClass("btn-default");
        }
    },

    render_commission_dashboard(frm) {
        if (frm.doc.__islocal) return;

        const base = flt(frm.doc.base_amount);
        const amount = flt(frm.doc.commission_amount);
        const currency = frappe.boot.sysdefaults.currency || "USD";
        const role = frm.doc.commission_role || "Salesperson";
        const role_color = role === "Manager" ? "#f5a623" : "#5e64ff";
        const is_reversal = base < 0;

        const status_config = {
            "Pending": { color: "#f5a623", bg: "#fef3e0", icon: "⏳" },
            "Approved": { color: "#2196f3", bg: "#e3f2fd", icon: "✔️" },
            "Paid": { color: "#36b37e", bg: "#e6f9f0", icon: "✅" },
            "Cancelled": { color: "#de3618", bg: "#fce8e6", icon: "❌" },
            "Reversed": { color: "#9c27b0", bg: "#f3e5f5", icon: "↩️" },
        };
        const st = status_config[frm.doc.status] || status_config["Pending"];

        const section = frm.fields_dict.invoice_section;
        const wrapper = section.$wrapper || section.wrapper;
        $(wrapper).find(".commission-dashboard").remove();

        const html = `
        <div class="commission-dashboard" style="margin:10px 0 20px 0;">
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <div style="flex:1; min-width:140px; background:#f8f9fc; border-radius:10px;
                    padding:16px; border-left:4px solid #6c7ae0;">
                    <div style="font-size:11px; color:#8d99ae; text-transform:uppercase; font-weight:600;
                        letter-spacing:0.5px; margin-bottom:4px;">Invoice Amount</div>
                    <div style="font-size:20px; font-weight:700; color:${is_reversal ? '#de3618' : '#2d3748'};">
                        ${format_currency(base, currency)}
                    </div>
                    ${is_reversal ? '<div style="font-size:10px; color:#de3618; margin-top:2px;">↩ REVERSAL / CREDIT NOTE</div>' : ''}
                </div>

                <div style="flex:1; min-width:140px; background:#f0f4ff; border-radius:10px;
                    padding:16px; border-left:4px solid ${role_color};">
                    <div style="font-size:11px; color:#8d99ae; text-transform:uppercase; font-weight:600;
                        letter-spacing:0.5px; margin-bottom:4px;">
                        <span style="background:${role_color}; color:#fff; padding:1px 6px;
                            border-radius:8px; font-size:9px;">${role}</span>
                        ${flt(frm.doc.commission_pct, 2)}%
                    </div>
                    <div style="font-size:20px; font-weight:700; color:${is_reversal ? '#de3618' : role_color};">
                        ${format_currency(amount, currency)}
                    </div>
                    <div style="font-size:11px; color:#6b7280; margin-top:2px;">
                        ${frm.doc.sales_person_name || frm.doc.sales_person || "—"}
                    </div>
                </div>

                <div style="flex:1; min-width:140px; background:${st.bg}; border-radius:10px;
                    padding:16px; border-left:4px solid ${st.color};">
                    <div style="font-size:11px; color:#8d99ae; text-transform:uppercase; font-weight:600;
                        letter-spacing:0.5px; margin-bottom:4px;">Status</div>
                    <div style="font-size:20px; font-weight:700; color:${st.color};">
                        ${st.icon} ${frm.doc.status}
                    </div>
                    ${frm.doc.approved_by ? `<div style="font-size:10px; color:#6b7280; margin-top:2px;">By: ${frm.doc.approved_by}</div>` : ''}
                </div>
            </div>
        </div>`;

        $(wrapper).prepend(html);
    },

    commission_pct(frm) {
        frm.trigger("calculate_amounts");
    },
    base_amount(frm) {
        frm.trigger("calculate_amounts");
    },
    calculate_amounts(frm) {
        const base = flt(frm.doc.base_amount);
        frm.set_value("commission_amount", base * flt(frm.doc.commission_pct) / 100);
    },

    set_status_indicator(frm) {
        const colors = {
            "Pending": "orange",
            "Approved": "blue",
            "Paid": "green",
            "Cancelled": "red",
            "Reversed": "purple",
        };
        frm.page.set_indicator(frm.doc.status, colors[frm.doc.status] || "gray");
    },
});
