# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe


def after_install():
	"""Set up default Commission Settings after app install."""
	_create_commission_accounts()
	_set_default_settings()


def _create_commission_accounts():
	"""Create Commission Expense and Payable accounts for every company."""
	for company in frappe.get_all("Company", pluck="name"):
		_ensure_account(
			company=company,
			account_name="Commission Expense",
			parent_account_type="Expense Account",
			parent_name_pattern="Indirect Expenses",
			root_type="Expense",
			account_type="Expense Account",
		)
		_ensure_account(
			company=company,
			account_name="Commission Payable",
			parent_account_type="",
			parent_name_pattern="Current Liabilities",
			root_type="Liability",
			account_type="Payable",
		)

	# Set the accounts in Commission Settings for the default company
	default_company = frappe.defaults.get_defaults().get("company")
	if default_company:
		abbr = frappe.get_cached_value("Company", default_company, "abbr")
		expense_acct = f"Commission Expense - {abbr}"
		payable_acct = f"Commission Payable - {abbr}"

		settings = frappe.get_doc("Commission Settings")
		if frappe.db.exists("Account", expense_acct):
			settings.commission_expense_account = expense_acct
		if frappe.db.exists("Account", payable_acct):
			settings.commission_payable_account = payable_acct
		settings.flags.ignore_permissions = True
		settings.save()


def _ensure_account(company, account_name, parent_account_type, parent_name_pattern, root_type, account_type):
	"""Create an account if it does not already exist."""
	abbr = frappe.get_cached_value("Company", company, "abbr")
	full_name = f"{account_name} - {abbr}"

	if frappe.db.exists("Account", full_name):
		return

	# Find parent account
	parent = _find_parent_account(company, parent_name_pattern, root_type)
	if not parent:
		return  # Skip if no suitable parent found

	account = frappe.new_doc("Account")
	account.update({
		"account_name": account_name,
		"company": company,
		"parent_account": parent,
		"root_type": root_type,
		"account_type": account_type,
		"is_group": 0,
	})
	account.flags.ignore_permissions = True
	account.insert()


def _find_parent_account(company, name_pattern, root_type):
	"""Find a suitable parent account by name pattern and root type."""
	abbr = frappe.get_cached_value("Company", company, "abbr")

	# Try exact match with abbreviation
	candidates = [
		f"{name_pattern} - {abbr}",
	]
	for candidate in candidates:
		if frappe.db.exists("Account", candidate):
			return candidate

	# Fall back: search by account_name LIKE pattern
	result = frappe.db.get_value(
		"Account",
		{"account_name": ("like", f"%{name_pattern}%"), "company": company, "is_group": 1},
		"name",
	)
	if result:
		return result

	# Last resort: any group account of same root_type
	result = frappe.db.get_value(
		"Account",
		{"root_type": root_type, "company": company, "is_group": 1},
		"name",
	)
	return result


def _set_default_settings():
	"""Ensure Commission Settings has auto_create_journal_entry ON."""
	settings = frappe.get_doc("Commission Settings")
	settings.auto_create_journal_entry = 1
	settings.flags.ignore_permissions = True
	settings.save()


def on_new_company(doc, method=None):
	"""Auto-create Commission Expense and Payable accounts for new companies."""
	_ensure_account(
		company=doc.name,
		account_name="Commission Expense",
		parent_account_type="Expense Account",
		parent_name_pattern="Indirect Expenses",
		root_type="Expense",
		account_type="Expense Account",
	)
	_ensure_account(
		company=doc.name,
		account_name="Commission Payable",
		parent_account_type="",
		parent_name_pattern="Current Liabilities",
		root_type="Liability",
		account_type="Payable",
	)
