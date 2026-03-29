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
		commission_role: DF.Literal["Salesperson", "Manager"]
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
		# Keep manager_commission_amount for backward compat, but new entries set it to 0
		self.manager_commission_amount = flt(self.base_amount) * flt(self.manager_commission_pct) / 100

	def on_update(self):
		"""Auto-create journal entry and notify when status changes to Paid."""
		if self.status == "Paid" and self.has_value_changed("status"):
			settings = frappe.get_cached_doc("Commission Settings")
			if (
				settings.auto_create_journal_entry
				and not self.journal_entry
				and settings.commission_expense_account
				and settings.commission_payable_account
			):
				self._create_journal_entry(settings)

			self._send_paid_notification()

	def _create_journal_entry(self, settings):
		# Each entry now represents ONE person — use their commission_amount only
		amount = flt(self.commission_amount)
		if not amount:
			return

		role_label = self.commission_role or "Salesperson"
		payee = self.sales_person_name or self.sales_person

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.posting_date = frappe.utils.today()
		je.user_remark = _(
			"Commission payment ({role}) for {person} — {entry} / {invoice}"
		).format(
			role=role_label,
			person=payee,
			entry=self.name,
			invoice=self.sales_invoice,
		)

		je.append("accounts", {
			"account": settings.commission_expense_account,
			"debit_in_account_currency": amount,
			"credit_in_account_currency": 0,
		})
		je.append("accounts", {
			"account": settings.commission_payable_account,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": amount,
		})

		je.flags.ignore_permissions = True
		je.insert()
		je.submit()

		self.db_set("journal_entry", je.name)
		frappe.msgprint(
			_("Journal Entry {0} created — {1} commission for {2}: {3}").format(
				je.name, role_label, payee, frappe.utils.fmt_money(amount)
			),
			indicator="green",
		)

	def _send_paid_notification(self):
		"""Send email notification to the person when their commission is paid."""
		recipients = []

		# The sales_person field holds the payee (could be SP or Manager)
		sp_employee = frappe.db.get_value("Sales Person", self.sales_person, "employee")
		if sp_employee:
			sp_email = (
				frappe.db.get_value("Employee", sp_employee, "prefered_email")
				or frappe.db.get_value("Employee", sp_employee, "company_email")
				or frappe.db.get_value("Employee", sp_employee, "personal_email")
			)
			if sp_email:
				recipients.append(sp_email)

		if not recipients:
			return

		role_label = self.commission_role or "Salesperson"
		payee = self.sales_person_name or self.sales_person
		amount = flt(self.commission_amount)

		subject = _("Commission Paid — {0} ({1})").format(self.name, role_label)
		message = _(
			"<p>Hello {person},</p>"
			"<p>Your <b>{role}</b> commission has been marked as <b>Paid</b>.</p>"
			"<table style='border-collapse:collapse; width:100%; max-width:500px;'>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Commission Entry</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{entry}</td></tr>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Role</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{role}</td></tr>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Sales Invoice</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{invoice}</td></tr>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Customer</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{customer}</td></tr>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Rate</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{pct}%</td></tr>"
			"<tr style='background:#f0f4ff;'><td style='padding:6px; border:1px solid #ddd;'><b>Amount</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'><b>{amount}</b></td></tr>"
			"</table>"
			"<p>Regards,<br>Commission Engine</p>"
		).format(
			person=payee,
			role=role_label,
			entry=self.name,
			invoice=self.sales_invoice,
			customer=self.customer_name or self.customer,
			pct=flt(self.commission_pct, 2),
			amount=frappe.utils.fmt_money(amount),
		)

		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				reference_doctype="Commission Entry",
				reference_name=self.name,
				now=False,
			)
		except Exception:
			frappe.log_error("Commission Paid Notification Error")


# ---------------------------------------------------------------------------
# Hook called on Sales Invoice submit
# ---------------------------------------------------------------------------

def create_commission_entries(doc, method=None):
	"""
	Triggered on Sales Invoice `on_submit`.
	Creates separate Commission Entries for each Sales Person AND their Manager.
	Each person gets their own independent entry that can be paid separately.
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

		# Pick global default rates from settings
		if is_first:
			sp_pct = flt(settings.onetime_salesperson_pct)
			mgr_pct = flt(settings.onetime_manager_pct)
		else:
			sp_pct = flt(settings.recurring_salesperson_pct)
			mgr_pct = flt(settings.recurring_manager_pct)

		# Check for individual override for this salesperson
		sp_pct = _get_override_rate(settings, row.sales_person, "Salesperson", is_first, sp_pct)

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

		# Check for individual override for this manager
		if manager:
			mgr_pct = _get_override_rate(settings, manager, "Manager", is_first, mgr_pct)

		# ---- ENTRY 1: Salesperson Commission ----
		existing_sp = frappe.db.exists("Commission Entry", {
			"sales_invoice": doc.name,
			"sales_person": row.sales_person,
			"commission_role": "Salesperson",
		})
		if not existing_sp:
			sp_entry = frappe.new_doc("Commission Entry")
			sp_entry.update({
				"sales_invoice": doc.name,
				"company": doc.company,
				"customer": doc.customer,
				"commission_type": commission_type,
				"commission_role": "Salesperson",
				"commission_month": get_first_day(getdate(doc.posting_date)),
				"sales_person": row.sales_person,
				"commission_pct": sp_pct,
				"base_amount": base_amount,
				"manager": manager,
				"manager_commission_pct": 0,
				"status": "Pending",
			})
			sp_entry.flags.ignore_permissions = True
			sp_entry.insert()

		# ---- ENTRY 2: Manager Commission (if manager exists and has rate) ----
		if manager and mgr_pct:
			existing_mgr = frappe.db.exists("Commission Entry", {
				"sales_invoice": doc.name,
				"sales_person": manager,
				"commission_role": "Manager",
			})
			if not existing_mgr:
				mgr_entry = frappe.new_doc("Commission Entry")
				mgr_entry.update({
					"sales_invoice": doc.name,
					"company": doc.company,
					"customer": doc.customer,
					"commission_type": commission_type,
					"commission_role": "Manager",
					"commission_month": get_first_day(getdate(doc.posting_date)),
					"sales_person": manager,  # Manager is the payee
					"commission_pct": mgr_pct,
					"base_amount": base_amount,
					"manager": None,
					"manager_commission_pct": 0,
					"status": "Pending",
				})
				mgr_entry.flags.ignore_permissions = True
				mgr_entry.insert()

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


def _get_override_rate(settings, sales_person, role, is_first, default_pct):
	overrides = settings.get("commission_rate_overrides") or []
	for row in overrides:
		if row.sales_person == sales_person and row.role == role:
			if is_first:
				rate = flt(row.onetime_commission_pct)
			else:
				rate = flt(row.recurring_commission_pct)
			if rate:
				return rate
			break
	return default_pct
