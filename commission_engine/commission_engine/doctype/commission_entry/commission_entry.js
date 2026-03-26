// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Entry", {
    refresh(frm) {
        frm.trigger("set_status_indicator");

        // Add "Mark as Paid" button for pending entries
        if (frm.doc.status === "Pending" && !frm.doc.__islocal) {
            frm.add_custom_button(__("Mark as Paid"), () => {
                frappe.confirm(
                    __("Mark this commission as Paid? This may auto-create a Journal Entry if configured."),
                    () => {
                        frm.set_value("status", "Paid");
                        frm.save();
                    }
                );
            }, __("Actions")).addClass("btn-success");
        }

        // Show commission breakdown in dashboard area
        frm.trigger("show_commission_summary");
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

    show_commission_summary(frm) {
        if (frm.doc.base_amount) {
            const sp_amt = flt(frm.doc.commission_amount).toFixed(2);
            const mgr_amt = flt(frm.doc.manager_commission_amount).toFixed(2);
            const total = (flt(frm.doc.commission_amount) + flt(frm.doc.manager_commission_amount)).toFixed(2);
            frm.dashboard.add_comment(
                `<b>💰 Commission Breakdown:</b> Salesperson: <b>${sp_amt}</b> | Manager: <b>${mgr_amt}</b> | Total: <b>${total}</b>`,
                "blue",
                true
            );
        }
    },
});
