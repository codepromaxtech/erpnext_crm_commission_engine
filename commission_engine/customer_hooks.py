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

	# Get commission rates from settings
	sp_pct = 0
	mgr_pct = 0
	try:
		settings = frappe.get_cached_doc("Commission Settings")
		sp_pct = flt(settings.onetime_salesperson_pct) or 0
		mgr_pct = flt(settings.onetime_manager_pct) or 0
	except Exception:
		pass

	# Resolve manager from Sales Person tree (parent node)
	manager = None
	manager_name = None
	lft, rgt, parent_sp = frappe.db.get_value(
		"Sales Person", sales_person, ["lft", "rgt", "parent_sales_person"]
	) or (0, 0, None)

	if parent_sp and parent_sp not in ("All Sales Persons", ""):
		manager = parent_sp
		manager_name = frappe.db.get_value("Sales Person", manager, "sales_person_name")

	return {
		"sales_person": sales_person,
		"commission_rate": sp_pct,
		"manager": manager,
		"manager_name": manager_name,
		"manager_commission_rate": mgr_pct,
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


def protect_sales_person_assignment(doc, method=None):
	"""
	On Customer.validate — prevent Sales Users from changing the sales_team
	assignment. Only managers in the hierarchy (or System/Accounts Manager)
	can reassign a customer's sales person.

	This prevents lead/customer "stealing" between salespeople.
	"""
	if doc.is_new():
		return

	# Privileged roles can always change
	user_roles = frappe.get_roles(frappe.session.user)
	privileged_roles = {"System Manager", "Accounts Manager", "Administrator"}
	if privileged_roles & set(user_roles):
		return

	# Get current DB state of sales_team
	old_sales_persons = set(
		frappe.db.get_all(
			"Sales Team",
			filters={"parenttype": "Customer", "parent": doc.name},
			pluck="sales_person",
		)
	)

	if not old_sales_persons:
		return  # No existing assignment to protect

	# Get new sales_team from the form
	new_sales_persons = set(
		row.sales_person for row in (doc.get("sales_team") or []) if row.sales_person
	)

	# Check for removed or changed sales persons
	removed = old_sales_persons - new_sales_persons
	added = new_sales_persons - old_sales_persons

	if not removed and not added:
		return  # No changes to protect

	# Resolve the current user to their Sales Person
	user_sp = _resolve_sales_person(frappe.session.user)

	# For each removed sales person, verify the current user is a manager
	for old_sp in removed:
		if not _is_manager_of(user_sp, old_sp):
			frappe.throw(
				frappe._(
					"You cannot remove <b>{0}</b> from this customer's sales team. "
					"Only their manager or a System Manager can reassign customers."
				).format(old_sp),
				title=frappe._("Sales Person Protected"),
			)

	# If a sales person was replaced, also verify for the original
	if removed and added:
		for old_sp in removed:
			if not _is_manager_of(user_sp, old_sp):
				frappe.throw(
					frappe._(
						"You cannot reassign this customer from <b>{0}</b>. "
						"Only their manager or a System Manager can make this change."
					).format(old_sp),
					title=frappe._("Sales Person Protected"),
				)


def _is_manager_of(manager_sp, subordinate_sp):
	"""
	Check if manager_sp is an ancestor of subordinate_sp in the Sales Person tree.
	Uses the nested set model (lft/rgt) for efficient ancestor checking.
	"""
	if not manager_sp or not subordinate_sp:
		return False

	if manager_sp == subordinate_sp:
		return True  # Same person

	# Use nested set: manager's lft < subordinate's lft < subordinate's rgt < manager's rgt
	mgr_lft, mgr_rgt = frappe.db.get_value(
		"Sales Person", manager_sp, ["lft", "rgt"]
	) or (0, 0)
	sub_lft, sub_rgt = frappe.db.get_value(
		"Sales Person", subordinate_sp, ["lft", "rgt"]
	) or (0, 0)

	if mgr_lft and sub_lft:
		return mgr_lft < sub_lft and sub_rgt < mgr_rgt

	# Fallback: walk up the tree manually
	current = subordinate_sp
	for _ in range(10):  # Safety limit
		parent = frappe.db.get_value("Sales Person", current, "parent_sales_person")
		if not parent or parent == current:
			return False
		if parent == manager_sp:
			return True
		current = parent

	return False

