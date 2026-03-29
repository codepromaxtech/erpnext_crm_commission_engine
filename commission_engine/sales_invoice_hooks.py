# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

"""
Sales Invoice hooks for Commission Engine.

Ensures subscription-generated (or any) Sales Invoices inherit the
sales_team from the Customer record when not already set.
"""

import frappe
from frappe.utils import flt


def auto_populate_sales_team(doc, method=None):
	"""
	On Sales Invoice validate, if no sales_team is present,
	copy the customer's default sales_team.

	This ensures subscription-generated invoices (which bypass the UI)
	properly inherit the sales person for commission calculation.
	"""
	if doc.get("sales_team") and len(doc.get("sales_team")) > 0:
		return

	if not doc.customer:
		return

	# Fetch the customer's default sales_team
	customer_sales_team = frappe.get_all(
		"Sales Team",
		filters={"parent": doc.customer, "parenttype": "Customer"},
		fields=["sales_person", "allocated_percentage", "allocated_amount", "commission_rate"],
	)

	if not customer_sales_team:
		return

	for row in customer_sales_team:
		doc.append("sales_team", {
			"sales_person": row.sales_person,
			"allocated_percentage": flt(row.allocated_percentage) or 100,
			"allocated_amount": flt(row.allocated_amount) or flt(doc.base_net_total),
			"commission_rate": flt(row.commission_rate) or 0,
		})

	frappe.msgprint(
		frappe._(
			"Sales Team auto-populated from Customer <b>{0}</b> defaults."
		).format(doc.customer),
		indicator="blue",
		alert=True,
	)
