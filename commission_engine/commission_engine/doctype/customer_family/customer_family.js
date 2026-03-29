// Copyright (c) 2026, CodeProMax Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer Family", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.trigger("render_family_dashboard");
        }
    },

    render_family_dashboard(frm) {
        const members = frm.doc.members || [];
        const member_count = members.length;
        const primary = frm.doc.primary_customer || "Not set";

        // Count relation types
        const types = {};
        members.forEach(m => {
            types[m.relation_type] = (types[m.relation_type] || 0) + 1;
        });

        const type_badges = Object.entries(types).map(([type, count]) => {
            const colors = {
                "Parent": "#5e64ff", "Child": "#29cd42", "Spouse": "#e91e63",
                "Sibling": "#ff9800", "Related": "#9c27b0", "Subsidiary": "#00bcd4",
                "Branch": "#607d8b"
            };
            const color = colors[type] || "#6b7280";
            return `<span style="background:${color}; color:#fff; padding:2px 8px;
                border-radius:10px; font-size:10px; font-weight:600; margin-right:4px;">${count} ${type}</span>`;
        }).join("");

        const html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px;
            padding: 20px 24px; color: #fff; margin: 10px 0 16px 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                <span style="font-size: 22px;">👨‍👩‍👧‍👦</span>
                <span style="font-size: 16px; font-weight: 700;">Family Overview</span>
            </div>
            <div style="display: flex; gap: 24px; margin-bottom: 8px;">
                <div>
                    <div style="font-size: 10px; opacity: 0.8;">Members</div>
                    <div style="font-size: 24px; font-weight: 700;">${member_count}</div>
                </div>
                <div>
                    <div style="font-size: 10px; opacity: 0.8;">Primary Customer</div>
                    <div style="font-size: 14px; font-weight: 600;">${primary}</div>
                </div>
            </div>
            <div>${type_badges}</div>
        </div>`;

        $(frm.fields_dict.family_section.$wrapper || frm.fields_dict.family_section.wrapper)
            .find(".family-dashboard").remove();
        $(frm.fields_dict.family_section.$wrapper || frm.fields_dict.family_section.wrapper)
            .prepend(`<div class="family-dashboard">${html}</div>`);
    },

    primary_customer(frm) { frm.trigger("render_family_dashboard"); },
});
