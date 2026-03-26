# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, get_first_day


class CommissionEntry(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_amount: DF.Currency
		commission_amount: DF.Currency
		commission_month: DF.Date
		commission_pct: DF.Percent
		commission_type: DF.Literal["One-Time", "Recurring"]
		company: DF.Link
		customer: DF.Link | None
		customer_name: DF.Data | None
		journal_entry: DF.Link | None
		manager: DF.Link | None
		manager_commission_amount: DF.Currency
		manager_commission_pct: DF.Percent
		manager_name: DF.Data | None
		sales_invoice: DF.Link
		sales_person: DF.Link
		sales_person_name: DF.Data | None
		status: DF.Literal["Pending", "Paid", "Cancelled"]
		subscription: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.commission_amount = flt(self.base_amount) * flt(self.commission_pct) / 100
		self.manager_commission_amount = flt(self.base_amount) * flt(self.manager_commission_pct) / 100

	def on_update(self):
		"""Auto-create journal entry when status is set to Paid and setting is enabled."""
		settings = frappe.get_cached_doc("Commission Settings")
		if (
			self.status == "Paid"
			and settings.auto_create_journal_entry
			and not self.journal_entry
			and settings.commission_expense_account
			and settings.commission_payable_account
		):
			self._create_journal_entry(settings)

	def _create_journal_entry(self, settings):
		total_amount = flt(self.commission_amount) + flt(self.manager_commission_amount)
		if not total_amount:
			return

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.posting_date = frappe.utils.today()
		je.user_remark = _(f"Commission payment for {self.name} - {self.sales_invoice}")

		je.append("accounts", {
			"account": settings.commission_expense_account,
			"debit_in_account_currency": total_amount,
			"credit_in_account_currency": 0,
		})
		je.append("accounts", {
			"account": settings.commission_payable_account,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": total_amount,
		})

		je.flags.ignore_permissions = True
		je.insert()
		je.submit()

		self.db_set("journal_entry", je.name)
		frappe.msgprint(_(f"Journal Entry {je.name} created for commission payment."), indicator="green")


# ---------------------------------------------------------------------------
# Hook called on Sales Invoice submit
# ---------------------------------------------------------------------------

def create_commission_entries(doc, method=None):
	"""
	Triggered on Sales Invoice `on_submit`.
	Creates one Commission Entry per Sales Team row on the invoice.
	"""
	if doc.is_return:
		return  # No commission on credit notes

	settings = frappe.get_cached_doc("Commission Settings")
	sales_team = doc.get("sales_team") or []

	if not sales_team:
		return  # No sales team tagged, skip silently

	for row in sales_team:
		if not row.sales_person:
			continue

		# Determine if this is the customer's first invoice (one-time) or recurring
		is_first = _is_first_invoice(doc.customer, doc.name)
		commission_type = "One-Time" if is_first else "Recurring"

		# Pick rates from settings
		if is_first:
			sp_pct = flt(settings.onetime_salesperson_pct)
			mgr_pct = flt(settings.onetime_manager_pct)
		else:
			sp_pct = flt(settings.recurring_salesperson_pct)
			mgr_pct = flt(settings.recurring_manager_pct)

		# Base amount = the allocated amount for this sales person on the invoice
		base_amount = flt(row.allocated_amount) or flt(doc.base_net_total)

		# Find manager via Sales Person tree (parent_sales_person)
		manager = frappe.db.get_value(
			"Sales Person", row.sales_person, "parent_sales_person"
		)
		# Exclude tree root ("All Sales Persons") as manager
		if manager:
			root = frappe.db.get_value(
				"Sales Person", {"is_group": 1, "parent_sales_person": ""}, "name"
			)
			if manager == root:
				manager = None

		# Check if a Commission Entry already exists for this invoice + salesperson
		existing = frappe.db.exists("Commission Entry", {
			"sales_invoice": doc.name,
			"sales_person": row.sales_person,
		})
		if existing:
			continue

		entry = frappe.new_doc("Commission Entry")
		entry.update({
			"sales_invoice": doc.name,
			"company": doc.company,
			"customer": doc.customer,
			"commission_type": commission_type,
			"commission_month": get_first_day(getdate(doc.posting_date)),
			"sales_person": row.sales_person,
			"commission_pct": sp_pct,
			"base_amount": base_amount,
			"manager": manager,
			"manager_commission_pct": mgr_pct if manager else 0,
			"status": "Pending",
		})
		entry.flags.ignore_permissions = True
		entry.insert()

	frappe.db.commit()


def cancel_commission_entries(doc, method=None):
	"""
	Triggered on Sales Invoice `on_cancel`.
	Cancels all Pending Commission Entries linked to this invoice.
	"""
	entries = frappe.get_all(
		"Commission Entry",
		filters={"sales_invoice": doc.name, "status": ["!=", "Paid"]},
		pluck="name",
	)
	for name in entries:
		frappe.db.set_value("Commission Entry", name, "status", "Cancelled")

	if entries:
		frappe.db.commit()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _is_first_invoice(customer, current_invoice_name):
	"""
	Returns True if this is the first submitted Sales Invoice for the customer.
	A 'first invoice' means no other submitted (docstatus=1) invoice exists
	for this customer before/excluding the current one.
	"""
	count = frappe.db.count(
		"Sales Invoice",
		filters={
			"customer": customer,
			"docstatus": 1,
			"name": ["!=", current_invoice_name],
			"is_return": 0,
		},
	)
	return count == 0
