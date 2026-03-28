// Commission Entry List View
frappe.listview_settings["Commission Entry"] = {
    add_fields: ["status", "commission_type", "commission_amount", "manager_commission_amount",
        "sales_person", "customer", "base_amount"],

    get_indicator: function (doc) {
        const indicators = {
            "Pending": [__("Pending"), "orange", "status,=,Pending"],
            "Paid": [__("Paid"), "green", "status,=,Paid"],
            "Cancelled": [__("Cancelled"), "red", "status,=,Cancelled"],
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

        commission_amount(val, df, doc) {
            const total = flt(val) + flt(doc.manager_commission_amount);
            if (total > 0) {
                return `<span style="font-weight: 600; color: #5e64ff;">
                    ${format_currency(total, frappe.boot.sysdefaults.currency)}</span>`;
            }
            return format_currency(0, frappe.boot.sysdefaults.currency);
        },
    },

    onload(listview) {
        // Quick filters
        listview.page.add_inner_button(__("Pending"), () => {
            listview.filter_area.add([[listview.doctype, "status", "=", "Pending"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("Paid"), () => {
            listview.filter_area.add([[listview.doctype, "status", "=", "Paid"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("One-Time"), () => {
            listview.filter_area.add([[listview.doctype, "commission_type", "=", "One-Time"]]);
        }, __("Quick Filter"));

        listview.page.add_inner_button(__("Recurring"), () => {
            listview.filter_area.add([[listview.doctype, "commission_type", "=", "Recurring"]]);
        }, __("Quick Filter"));

        // Bulk Mark as Paid action
        listview.page.add_action_item(__("Mark as Paid"), () => {
            const checked = listview.get_checked_items();
            const pending = checked.filter(d => d.status === "Pending");

            if (!pending.length) {
                frappe.msgprint(__("Please select at least one Pending commission entry."));
                return;
            }

            frappe.confirm(
                __("Mark {0} commission entries as Paid?", [pending.length]),
                () => {
                    frappe.xcall(
                        "commission_engine.api.bulk_mark_as_paid",
                        { names: pending.map(d => d.name) }
                    ).then(r => {
                        frappe.show_alert({
                            message: r.message,
                            indicator: "green"
                        });
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
            return __("Mark Paid");
        },
        get_description(doc) {
            return __("Mark {0} as Paid", [doc.name]);
        },
        action(doc) {
            frappe.xcall("frappe.client.set_value", {
                doctype: "Commission Entry",
                name: doc.name,
                fieldname: "status",
                value: "Paid"
            }).then(() => {
                frappe.show_alert({ message: __("Marked as Paid"), indicator: "green" });
                cur_list.refresh();
            });
        },
    },
};
