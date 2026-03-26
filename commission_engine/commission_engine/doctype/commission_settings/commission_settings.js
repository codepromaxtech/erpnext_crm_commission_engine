// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Settings", {
    refresh(frm) {
        frm.dashboard.add_comment(
            __("These rates apply globally to all Sales Invoices. " +
                "<b>First Invoice</b> rates apply when a salesperson bills a customer for the first time. " +
                "<b>Recurring</b> rates apply to all subsequent invoices for the same customer."),
            "blue",
            true
        );

        // Warn if both salesperson and manager rates are 0
        const allZero = [
            frm.doc.onetime_salesperson_pct,
            frm.doc.onetime_manager_pct,
            frm.doc.recurring_salesperson_pct,
            frm.doc.recurring_manager_pct,
        ].every(v => !v || v === 0);

        if (allZero) {
            frm.dashboard.add_comment(
                __("⚠️ All commission rates are currently 0%. Commission Entries will be created but with zero amounts."),
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
                    message: __("Please set the Commission Expense Account and Commission Payable Account to auto-create Journal Entries."),
                    indicator: "orange",
                });
            }
        }
    },
});
