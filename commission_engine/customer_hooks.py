# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt


@frappe.whitelist()
def resolve_sales_person_from_lead(lead_name):
	"""
	Whitelisted API: Given a Lead name, resolve the Lead Owner to a Sales Person
	and return the sales person name with commission rate for the Customer form.
	"""
	if not lead_name:
		return None

	lead_owner = frappe.db.get_value("Lead", lead_name, "lead_owner")
	if not lead_owner:
		return None

	sales_person = _resolve_sales_person(lead_owner)
	if not sales_person:
		return None

	# Get commission rate from settings
	commission_pct = 0
	try:
		settings = frappe.get_cached_doc("Commission Settings")
		commission_pct = flt(settings.onetime_salesperson_pct) or 0
	except Exception:
		pass

	return {
		"sales_person": sales_person,
		"commission_rate": commission_pct,
		"lead_owner": lead_owner,
	}


def auto_set_sales_person(doc, method=None):
	"""
	When a Customer is created from a Lead, auto-populate the sales_team
	by resolving: Lead.lead_owner (User) → Employee → Sales Person.

	This ensures subscription invoices and manual invoices for this customer
	always have a tagged sales person for commission calculation.

	Runs on Customer.before_insert so the sales_team is saved in a single
	database operation (no double-save needed).
	"""
	# Only run if customer has no sales_team already
	if doc.get("sales_team") and len(doc.get("sales_team")) > 0:
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

	# Get the default commission rate from Commission Settings
	commission_pct = 0
	try:
		settings = frappe.get_cached_doc("Commission Settings")
		commission_pct = flt(settings.onetime_salesperson_pct) or 0
	except Exception:
		pass

	# Add to sales_team with proper commission rate
	doc.append("sales_team", {
		"sales_person": sales_person,
		"allocated_percentage": 100,
		"allocated_amount": 0,
		"commission_rate": commission_pct,
	})

	frappe.msgprint(
		frappe._(
			"Sales Person <b>{0}</b> auto-assigned from Lead Owner <b>{1}</b> with {2}% commission."
		).format(sales_person, lead_owner, commission_pct),
		indicator="green",
		alert=True,
	)


def _resolve_sales_person(user_email):
	"""
	Resolve a User email to a Sales Person via:
	1. User → Employee (user_id field) → Sales Person (employee field)
	2. Employee name → Sales Person name match
	3. User full name → Sales Person name match
	"""
	# Method 1: User → Employee → Sales Person
	employee = frappe.db.get_value(
		"Employee", {"user_id": user_email, "status": "Active"}, "name"
	)
	if employee:
		sales_person = frappe.db.get_value(
			"Sales Person", {"employee": employee, "enabled": 1}, "name"
		)
		if sales_person:
			return sales_person

		# Method 2: Try matching by employee name
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
