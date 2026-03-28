# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


def auto_set_sales_person(doc, method=None):
	"""
	When a Customer is created from a Lead, auto-populate the sales_team
	by resolving: Lead.lead_owner (User) → Employee → Sales Person.

	This ensures subscription invoices and manual invoices for this customer
	always have a tagged sales person for commission calculation.
	"""
	# Only run if customer has no sales_team already and was created from a lead
	if doc.get("sales_team"):
		return

	lead_name = doc.get("lead_name")
	if not lead_name:
		return

	# Get the lead owner (User) from the lead
	lead_owner = frappe.db.get_value("Lead", lead_name, "lead_owner")
	if not lead_owner:
		return

	# Resolve User → Employee → Sales Person
	sales_person = _resolve_sales_person(lead_owner)
	if not sales_person:
		return

	# Add to sales_team
	doc.append("sales_team", {
		"sales_person": sales_person,
		"allocated_percentage": 100,
		"allocated_amount": 0,
	})

	# We need to save since this runs after insert
	doc.flags.ignore_permissions = True
	doc.save()

	frappe.msgprint(
		frappe._(
			"Sales Person <b>{0}</b> auto-assigned from Lead Owner."
		).format(sales_person),
		indicator="green",
		alert=True,
	)


def _resolve_sales_person(user_email):
	"""
	Resolve a User email to a Sales Person via:
	1. User → Employee (user_id field) → Sales Person (employee field)
	2. Or direct Sales Person name match
	"""
	# Method 1: User → Employee → Sales Person
	employee = frappe.db.get_value("Employee", {"user_id": user_email, "status": "Active"}, "name")
	if employee:
		sales_person = frappe.db.get_value("Sales Person", {"employee": employee, "enabled": 1}, "name")
		if sales_person:
			return sales_person

	# Method 2: Try matching by employee name
	if employee:
		employee_name = frappe.db.get_value("Employee", employee, "employee_name")
		if employee_name:
			sales_person = frappe.db.get_value(
				"Sales Person",
				{"sales_person_name": employee_name, "enabled": 1},
				"name",
			)
			if sales_person:
				return sales_person

	# Method 3: Try matching Sales Person name directly by user's full name
	full_name = frappe.db.get_value("User", user_email, "full_name")
	if full_name:
		sales_person = frappe.db.get_value(
			"Sales Person",
			{"sales_person_name": full_name, "enabled": 1},
			"name",
		)
		if sales_person:
			return sales_person

	return None
