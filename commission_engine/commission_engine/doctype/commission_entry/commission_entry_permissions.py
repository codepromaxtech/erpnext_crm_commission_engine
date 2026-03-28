# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

"""
Role-based permission logic for Commission Entry.

Access Rules:
- Sales User:    Can only see commissions where they are the sales_person
- Sales Manager: Can see commissions where they or their team members are the
                 sales_person or manager
- Accounts User / System Manager / Administrator: Can see all commissions
"""

import frappe


def get_permission_query_conditions(user=None):
	"""
	Called by Frappe to add WHERE conditions to list queries.
	Returns a SQL condition string that filters Commission Entries.
	"""
	if not user:
		user = frappe.session.user

	# Admin and Accounts User see everything
	if _is_privileged_user(user):
		return ""

	# Resolve the current user to a Sales Person
	sales_persons = _get_user_sales_persons(user)
	if not sales_persons:
		# User has no linked Sales Person — show nothing
		return "1=0"

	roles = frappe.get_roles(user)

	if "Sales Manager" in roles:
		# Get all descendants (team members) of this Sales Person
		all_persons = set(sales_persons)
		for sp in sales_persons:
			descendants = _get_descendants(sp)
			all_persons.update(descendants)

		persons_str = ", ".join(f"'{frappe.db.escape(p)}'" for p in all_persons)
		return (
			f"(`tabCommission Entry`.sales_person IN ({persons_str}) "
			f"OR `tabCommission Entry`.manager IN ({persons_str}))"
		)

	# Sales User — only their own commissions
	persons_str = ", ".join(f"'{frappe.db.escape(p)}'" for p in sales_persons)
	return f"`tabCommission Entry`.sales_person IN ({persons_str})"


def has_permission(doc, ptype=None, user=None):
	"""
	Called by Frappe to check if a user can access a specific Commission Entry.
	"""
	if not user:
		user = frappe.session.user

	# Admin and Accounts User see everything
	if _is_privileged_user(user):
		return True

	# Resolve the current user to Sales Person(s)
	sales_persons = _get_user_sales_persons(user)
	if not sales_persons:
		return False

	roles = frappe.get_roles(user)

	if "Sales Manager" in roles:
		# Manager can see their own + team members' commissions
		all_persons = set(sales_persons)
		for sp in sales_persons:
			descendants = _get_descendants(sp)
			all_persons.update(descendants)

		return doc.sales_person in all_persons or doc.manager in all_persons

	# Sales User — only their own
	return doc.sales_person in sales_persons


def _is_privileged_user(user):
	"""Check if user has admin/accounts privileges."""
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return bool({"System Manager", "Accounts User", "Accounts Manager"} & set(roles))


def _get_user_sales_persons(user):
	"""
	Resolve a User to their Sales Person(s).
	User → Employee → Sales Person
	"""
	# Find all active employees linked to this user
	employees = frappe.get_all(
		"Employee",
		filters={"user_id": user, "status": "Active"},
		pluck="name",
	)

	if not employees:
		return []

	# Find all Sales Persons linked to these employees
	sales_persons = frappe.get_all(
		"Sales Person",
		filters={"employee": ("in", employees), "enabled": 1},
		pluck="name",
	)

	return sales_persons


def _get_descendants(sales_person):
	"""Get all descendants of a Sales Person in the tree (NestedSet)."""
	lft, rgt = frappe.db.get_value("Sales Person", sales_person, ["lft", "rgt"]) or (0, 0)
	if not lft or not rgt:
		return []

	return frappe.get_all(
		"Sales Person",
		filters={"lft": (">", lft), "rgt": ("<", rgt), "enabled": 1},
		pluck="name",
	)
