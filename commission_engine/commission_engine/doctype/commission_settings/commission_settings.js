// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Settings", {
    refresh(frm) {
        frm.trigger("render_settings_dashboard");
        frm.trigger("validate_accounts");
    },

    render_settings_dashboard(frm) {
        // Remove previous
        $(frm.fields_dict.first_invoice_section.$wrapper || frm.fields_dict.first_invoice_section.wrapper)
            .find(".settings-dashboard").remove();

        const ot_sp = flt(frm.doc.onetime_salesperson_pct, 2);
        const ot_mgr = flt(frm.doc.onetime_manager_pct, 2);
        const rc_sp = flt(frm.doc.recurring_salesperson_pct, 2);
        const rc_mgr = flt(frm.doc.recurring_manager_pct, 2);
        const overrides = (frm.doc.commission_rate_overrides || []).length;
        const je_enabled = frm.doc.auto_create_journal_entry;

        const html = `
        <div class="settings-dashboard" style="margin: 10px 0 20px 0;">
            <!-- Info Banner -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px;
                padding: 20px 24px; color: #fff; margin-bottom: 16px;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <span style="font-size: 22px;">💰</span>
                    <span style="font-size: 16px; font-weight: 700;">Commission Engine Settings</span>
                </div>
                <div style="font-size: 13px; opacity: 0.9; line-height: 1.5;">
                    Configure global commission rates and per-person overrides.
                    <b>First Invoice</b> rates apply when a salesperson bills a customer for the first time.
                    <b>Recurring</b> rates apply to all subsequent invoices.
                </div>
            </div>

            <!-- Rate Summary Cards -->
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px;">
                <div style="flex: 1; min-width: 200px; background: #f0f4ff; border-radius: 10px; padding: 16px;">
                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 8px;">🆕 First Invoice Rates</div>
                    <div style="display: flex; gap: 16px;">
                        <div>
                            <div style="font-size: 10px; color: #9ca3af;">Salesperson</div>
                            <div style="font-size: 22px; font-weight: 700; color: #5e64ff;">${ot_sp}%</div>
                        </div>
                        <div>
                            <div style="font-size: 10px; color: #9ca3af;">Manager</div>
                            <div style="font-size: 22px; font-weight: 700; color: #818cf8;">${ot_mgr}%</div>
                        </div>
                    </div>
                </div>

                <div style="flex: 1; min-width: 200px; background: #f0fdf4; border-radius: 10px; padding: 16px;">
                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 8px;">🔄 Recurring Rates</div>
                    <div style="display: flex; gap: 16px;">
                        <div>
                            <div style="font-size: 10px; color: #9ca3af;">Salesperson</div>
                            <div style="font-size: 22px; font-weight: 700; color: #29cd42;">${rc_sp}%</div>
                        </div>
                        <div>
                            <div style="font-size: 10px; color: #9ca3af;">Manager</div>
                            <div style="font-size: 22px; font-weight: 700; color: #6ee7b7;">${rc_mgr}%</div>
                        </div>
                    </div>
                </div>

                <div style="flex: 1; min-width: 200px; background: #faf5ff; border-radius: 10px; padding: 16px;">
                    <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; font-weight: 600;
                        letter-spacing: 0.5px; margin-bottom: 8px;">⚙️ Configuration</div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="font-size: 14px;">${je_enabled ? '✅' : '⬜'}</span>
                            <span style="font-size: 12px; color: #374151;">Auto Journal Entries</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="font-size: 14px;">${overrides > 0 ? '👤' : '➖'}</span>
                            <span style="font-size: 12px; color: #374151;">
                                ${overrides > 0 ? overrides + ' person override(s)' : 'No individual overrides'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;

        const section = frm.fields_dict.first_invoice_section;
        const wrapper = section.$wrapper || section.wrapper;
        $(wrapper).prepend(html);
    },

    validate_accounts(frm) {
        if (frm.doc.auto_create_journal_entry) {
            if (!frm.doc.commission_expense_account || !frm.doc.commission_payable_account) {
                frm.dashboard.add_comment(
                    __("⚠️ Auto-Create Journal Entry is enabled but accounting accounts are not set. Please configure the Expense and Payable accounts below."),
                    "orange",
                    true
                );
            }
        }

        // Warn if all rates are 0
        const allZero = [
            frm.doc.onetime_salesperson_pct,
            frm.doc.onetime_manager_pct,
            frm.doc.recurring_salesperson_pct,
            frm.doc.recurring_manager_pct,
        ].every(v => !v || v === 0);

        if (allZero) {
            frm.dashboard.add_comment(
                __("⚠️ All default commission rates are 0%. Commissions will be created with zero amounts unless individual overrides are set."),
                "orange",
                true
            );
        }
    },

    auto_create_journal_entry(frm) {
        if (frm.doc.auto_create_journal_entry) {
            if (!frm.doc.commission_expense_account || !frm.doc.commission_payable_account) {
                frappe.msgprint({
                    title: __("Accounting Accounts Required"),
                    message: __("Please set the <b>Commission Expense Account</b> and <b>Commission Payable Account</b> in the Accounting section below to enable auto-creation of Journal Entries."),
                    indicator: "orange",
                });
            }
        }
    },

    onetime_salesperson_pct(frm) { frm.trigger("render_settings_dashboard"); },
    onetime_manager_pct(frm) { frm.trigger("render_settings_dashboard"); },
    recurring_salesperson_pct(frm) { frm.trigger("render_settings_dashboard"); },
    recurring_manager_pct(frm) { frm.trigger("render_settings_dashboard"); },
});
