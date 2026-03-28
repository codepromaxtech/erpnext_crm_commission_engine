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
                frappe.confirm(
                    __("Mark this commission as <b>Paid</b>? This will auto-create a Journal Entry if configured in Commission Settings."),
                    () => {
                        frm.set_value("status", "Paid");
                        frm.save().then(() => {
                            frappe.show_alert({
                                message: __("Commission marked as Paid"),
                                indicator: "green"
                            });
                        });
                    }
                );
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
