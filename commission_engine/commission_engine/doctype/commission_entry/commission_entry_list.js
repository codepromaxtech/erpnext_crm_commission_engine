// Commission Entry List View
frappe.listview_settings["Commission Entry"] = {
    add_fields: ["status", "commission_type", "commission_role", "commission_amount",
        "sales_person", "customer", "base_amount", "original_entry"],

    get_indicator: function (doc) {
        const indicators = {
            "Pending": [__("Pending"), "orange", "status,=,Pending"],
            "Approved": [__("Approved"), "blue", "status,=,Approved"],
            "Paid": [__("Paid"), "green", "status,=,Paid"],
            "Cancelled": [__("Cancelled"), "red", "status,=,Cancelled"],
            "Reversed": [__("Reversed"), "purple", "status,=,Reversed"],
        };
        return indicators[doc.status] || [__("Unknown"), "gray"];
    },

    formatters: {
        commission_type(val) {
            if (val === "One-Time") {
                return `<span class="indicator-pill whitespace-nowrap blue">
                    <span class="indicator blue"></span>${val}</span>`;
            }
            return `<span class="indicator-pill whitespace-nowrap green">
                <span class="indicator green"></span>${val}</span>`;
        },

        commission_role(val) {
            if (val === "Manager") {
                return `<span class="indicator-pill whitespace-nowrap orange">
                    <span class="indicator orange"></span>${val}</span>`;
            }
            return `<span class="indicator-pill whitespace-nowrap blue">
                <span class="indicator blue"></span>${val || "Salesperson"}</span>`;
        },

        commission_amount(val, df, doc) {
            const amt = flt(val);
            const color = amt < 0 ? "#de3618" : "#5e64ff";
            return `<span style="font-weight:600; color:${color};">
                ${format_currency(amt, frappe.boot.sysdefaults.currency)}</span>`;
        },
    },

    onload(listview) {
        // Quick filters
        listview.page.add_inner_button(__("Pending"), () => {
            listview.filter_area.add([[listview.doctype, "status", "=", "Pending"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("Approved"), () => {
            listview.filter_area.add([[listview.doctype, "status", "=", "Approved"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("Paid"), () => {
            listview.filter_area.add([[listview.doctype, "status", "=", "Paid"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("Salesperson"), () => {
            listview.filter_area.add([[listview.doctype, "commission_role", "=", "Salesperson"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("Manager"), () => {
            listview.filter_area.add([[listview.doctype, "commission_role", "=", "Manager"]]);
        }, __("Quick Filter"));

        // Bulk Approve
        listview.page.add_action_item(__("Bulk Approve"), () => {
            const checked = listview.get_checked_items();
            const pending = checked.filter(d => d.status === "Pending");
            if (!pending.length) {
                frappe.msgprint(__("Select Pending entries to approve."));
                return;
            }
            frappe.confirm(
                __("Approve {0} commission entries?", [pending.length]),
                () => {
                    frappe.xcall(
                        "commission_engine.api.bulk_approve",
                        { names: pending.map(d => d.name) }
                    ).then(r => {
                        frappe.show_alert({ message: r.message, indicator: "blue" });
                        listview.refresh();
                    });
                }
            );
        });

        // Bulk Mark as Paid
        listview.page.add_action_item(__("Bulk Mark as Paid"), () => {
            const checked = listview.get_checked_items();
            const payable = checked.filter(d => d.status === "Approved" || d.status === "Pending");
            if (!payable.length) {
                frappe.msgprint(__("Select Pending or Approved entries to pay."));
                return;
            }
            frappe.confirm(
                __("Mark {0} commission entries as Paid?", [payable.length]),
                () => {
                    frappe.xcall(
                        "commission_engine.api.bulk_mark_as_paid",
                        { names: payable.map(d => d.name) }
                    ).then(r => {
                        frappe.show_alert({ message: r.message, indicator: "green" });
                        listview.refresh();
                    });
                }
            );
        });
    },

    button: {
        show(doc) {
            return doc.status === "Pending";
        },
        get_label() {
            return __("Approve");
        },
        get_description(doc) {
            return __("Approve {0}", [doc.name]);
        },
        action(doc) {
            frappe.xcall("commission_engine.api.bulk_approve", {
                names: [doc.name]
            }).then(() => {
                frappe.show_alert({ message: __("Approved ✓"), indicator: "blue" });
                cur_list.refresh();
            });
        },
    },
};
