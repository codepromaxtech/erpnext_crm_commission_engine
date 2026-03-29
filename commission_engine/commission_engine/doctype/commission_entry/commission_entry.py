# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, get_first_day, nowdate, now


# Valid status transitions
VALID_TRANSITIONS = {
	"Pending": ["Approved", "Paid", "Cancelled"],
	"Approved": ["Paid", "Cancelled"],
	"Paid": ["Reversed"],   # Only system can do this (clawback)
	"Cancelled": [],
	"Reversed": [],
}


class CommissionEntry(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approval_date: DF.Datetime | None
		approved_by: DF.Link | None
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
		original_entry: DF.Link | None
		reversed_entry: DF.Link | None
		sales_invoice: DF.Link
		sales_person: DF.Link
		sales_person_name: DF.Data | None
		status: DF.Literal["Pending", "Approved", "Paid", "Cancelled", "Reversed"]
		subscription: DF.Link | None
	# end: auto-generated types

	def validate(self):
		# Check if the period is locked
		if self.commission_month and not self.flags.ignore_period_lock:
			from commission_engine.commission_engine.doctype.commission_period.commission_period import is_period_locked
			if is_period_locked(self.commission_month):
				frappe.throw(
					_("Commission period {0} is locked. No modifications allowed.").format(
						self.commission_month)
				)

		# Calculate commission amount
		self.commission_amount = flt(self.base_amount) * flt(self.commission_pct) / 100

		# Apply maximum cap
		settings = frappe.get_cached_doc("Commission Settings")
		cap = flt(settings.maximum_commission_cap)
		if cap > 0 and flt(self.commission_amount) > cap:
			self.commission_amount = cap

		# Backward compat
		self.manager_commission_amount = flt(self.base_amount) * flt(self.manager_commission_pct) / 100

		# Validate status transition
		if not self.is_new():
			self._validate_status_transition(settings)

	def _validate_status_transition(self, settings):
		"""Ensure only valid status transitions are allowed."""
		old_status = self.get_db_value("status")
		new_status = self.status

		if old_status == new_status:
			return  # No change

		if not old_status:
			return  # New document

		allowed = VALID_TRANSITIONS.get(old_status, [])
		if new_status not in allowed:
			frappe.throw(
				_("Invalid status transition: {0} → {1}. Allowed transitions from {0}: {2}").format(
					old_status, new_status, ", ".join(allowed) or "None"
				)
			)

		# Enforce approval workflow: block Pending → Paid if approval is enabled
		if (
			old_status == "Pending"
			and new_status == "Paid"
			and settings.enable_approval_workflow
		):
			frappe.throw(
				_("This commission must be Approved before it can be marked as Paid. "
				  "Approval workflow is enabled in Commission Settings.")
			)

	def on_update(self):
		"""Handle status transitions."""
		if not self.has_value_changed("status"):
			return

		if self.status == "Approved":
			self._on_approved()
		elif self.status == "Paid":
			self._on_paid()

	def _on_approved(self):
		"""Record who approved and when."""
		self.db_set("approved_by", frappe.session.user)
		self.db_set("approval_date", now())

	def _on_paid(self):
		"""Auto-create journal entry and send notification."""
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
		amount = flt(self.commission_amount)
		if not amount:
			return

		role_label = self.commission_role or "Salesperson"
		payee = self.sales_person_name or self.sales_person
		is_reversal = flt(amount) < 0

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.posting_date = nowdate()

		if is_reversal:
			je.user_remark = _(
				"Commission REVERSAL ({role}) for {person} — {entry} / {invoice}"
			).format(role=role_label, person=payee, entry=self.name, invoice=self.sales_invoice)
			# Reverse: credit expense, debit payable
			je.append("accounts", {
				"account": settings.commission_expense_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": abs(amount),
			})
			je.append("accounts", {
				"account": settings.commission_payable_account,
				"debit_in_account_currency": abs(amount),
				"credit_in_account_currency": 0,
			})
		else:
			je.user_remark = _(
				"Commission payment ({role}) for {person} — {entry} / {invoice}"
			).format(role=role_label, person=payee, entry=self.name, invoice=self.sales_invoice)
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
		action = "reversal" if is_reversal else "payment"
		frappe.msgprint(
			_("Journal Entry {0} created — {1} commission {2} for {3}: {4}").format(
				je.name, role_label, action, payee, frappe.utils.fmt_money(abs(amount))
			),
			indicator="green" if not is_reversal else "orange",
		)

	def _send_paid_notification(self):
		"""Send email notification to the person when their commission is paid."""
		recipients = []
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
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Entry</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{entry}</td></tr>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Invoice</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{invoice}</td></tr>"
			"<tr><td style='padding:6px; border:1px solid #ddd;'><b>Customer</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'>{customer}</td></tr>"
			"<tr style='background:#f0f4ff;'><td style='padding:6px; border:1px solid #ddd;'><b>Amount</b></td>"
			"<td style='padding:6px; border:1px solid #ddd;'><b>{amount}</b></td></tr>"
			"</table>"
			"<p>Regards,<br>Commission Engine</p>"
		).format(
			person=payee, role=role_label, entry=self.name,
			invoice=self.sales_invoice,
			customer=self.customer_name or self.customer,
			amount=frappe.utils.fmt_money(amount),
		)

		try:
			frappe.sendmail(
				recipients=recipients, subject=subject, message=message,
				reference_doctype="Commission Entry", reference_name=self.name,
				now=False,
			)
		except Exception:
			frappe.log_error("Commission Paid Notification Error")


# ---------------------------------------------------------------------------
# Hooks on Sales Invoice
# ---------------------------------------------------------------------------

def create_commission_entries(doc, method=None):
	"""
	Triggered on Sales Invoice `on_submit`.
	Creates separate Commission Entries for Salesperson AND Manager.

	Handles:
	- Normal invoices (positive amounts)
	- Credit notes / returns (negative reversal entries)
	- Amended invoices (cancel old entries, create new ones)
	"""
	settings = frappe.get_cached_doc("Commission Settings")
	sales_team = doc.get("sales_team") or []

	if not sales_team:
		return

	# --- Handle credit notes / returns ---
	if doc.is_return:
		_create_reversal_entries(doc, settings)
		return

	# --- Handle amended invoices ---
	if doc.amended_from:
		_cancel_entries_for_invoice(doc.amended_from)

	# --- Normal invoice flow ---
	for row in sales_team:
		if not row.sales_person:
			continue

		is_first = _is_first_invoice(doc.customer, doc.name)
		commission_type = "One-Time" if is_first else "Recurring"

		# Global default rates
		if is_first:
			sp_pct = flt(settings.onetime_salesperson_pct)
			mgr_pct = flt(settings.onetime_manager_pct)
		else:
			sp_pct = flt(settings.recurring_salesperson_pct)
			mgr_pct = flt(settings.recurring_manager_pct)

		# Per-person overrides
		sp_pct = _get_override_rate(settings, row.sales_person, "Salesperson", is_first, sp_pct)

		base_amount = flt(row.allocated_amount) or flt(doc.base_net_total)

		# Tiered commission (overrides flat rates if enabled)
		tiered_pct = _get_tiered_rate(settings, row.sales_person, base_amount, doc.posting_date)
		if tiered_pct is not None:
			sp_pct = tiered_pct

		# Find manager via Sales Person tree
		manager = frappe.db.get_value("Sales Person", row.sales_person, "parent_sales_person")
		if manager:
			root = frappe.db.get_value("Sales Person", {"is_group": 1, "parent_sales_person": ""}, "name")
			if manager == root:
				manager = None

		if manager:
			mgr_pct = _get_override_rate(settings, manager, "Manager", is_first, mgr_pct)

		# --- Create Salesperson Entry ---
		sp_amount = flt(base_amount) * flt(sp_pct) / 100
		cap = flt(settings.maximum_commission_cap)
		if cap > 0 and sp_amount > cap:
			sp_amount = cap

		min_threshold = flt(settings.minimum_commission_threshold)
		if min_threshold > 0 and sp_amount < min_threshold:
			pass  # Skip — below minimum
		else:
			existing = frappe.db.exists("Commission Entry", {
				"sales_invoice": doc.name,
				"sales_person": row.sales_person,
				"commission_role": "Salesperson",
			})
			if not existing:
				_insert_commission_entry(doc, row.sales_person, sp_pct, base_amount,
					commission_type, "Salesperson", manager)

		# --- Create Manager Entry ---
		if manager and mgr_pct:
			mgr_amount = flt(base_amount) * flt(mgr_pct) / 100
			if cap > 0 and mgr_amount > cap:
				mgr_amount = cap

			if min_threshold > 0 and mgr_amount < min_threshold:
				pass  # Skip — below minimum
			else:
				existing = frappe.db.exists("Commission Entry", {
					"sales_invoice": doc.name,
					"sales_person": manager,
					"commission_role": "Manager",
				})
				if not existing:
					_insert_commission_entry(doc, manager, mgr_pct, base_amount,
						commission_type, "Manager", None)

	frappe.db.commit()


def cancel_commission_entries(doc, method=None):
	"""
	Triggered on Sales Invoice `on_cancel`.
	- Pending/Approved entries → set to Cancelled
	- Paid entries → create REVERSAL (clawback) entries with negative amounts + reversal JE
	"""
	entries = frappe.get_all(
		"Commission Entry",
		filters={"sales_invoice": doc.name, "status": ["not in", ["Cancelled", "Reversed"]]},
		fields=["name", "status", "sales_person", "commission_pct", "base_amount",
		        "commission_role", "commission_type", "company", "customer",
		        "commission_month", "manager", "commission_amount"],
	)

	settings = frappe.get_cached_doc("Commission Settings")

	for entry in entries:
		if entry.status in ("Pending", "Approved"):
			# Simply cancel
			frappe.db.set_value("Commission Entry", entry.name, "status", "Cancelled")
		elif entry.status == "Paid":
			# CLAWBACK: Create reversal entry with negative amount
			_create_clawback_entry(entry, settings)

	if entries:
		frappe.db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_commission_entry(doc, sales_person, pct, base_amount,
                             commission_type, role, manager):
	"""Create and insert a single Commission Entry."""
	entry = frappe.new_doc("Commission Entry")
	entry.update({
		"sales_invoice": doc.name,
		"company": doc.company,
		"customer": doc.customer,
		"commission_type": commission_type,
		"commission_role": role,
		"commission_month": get_first_day(getdate(doc.posting_date)),
		"sales_person": sales_person,
		"commission_pct": pct,
		"base_amount": base_amount,
		"manager": manager,
		"manager_commission_pct": 0,
		"status": "Pending",
	})
	entry.flags.ignore_permissions = True
	entry.insert()
	return entry.name


def _create_reversal_entries(doc, settings):
	"""
	For credit notes (is_return=1): find original invoice's commission
	entries and create negative reversal entries.
	"""
	original_invoice = doc.return_against
	if not original_invoice:
		return

	original_entries = frappe.get_all(
		"Commission Entry",
		filters={
			"sales_invoice": original_invoice,
			"status": ["in", ["Pending", "Approved", "Paid"]],
			"reversed_entry": ["is", "not set"],
		},
		fields=["name", "sales_person", "commission_pct", "base_amount",
		        "commission_role", "commission_type", "company", "customer",
		        "commission_month", "manager", "commission_amount"],
	)

	for orig in original_entries:
		# Check if already reversed
		already_reversed = frappe.db.exists("Commission Entry", {
			"original_entry": orig.name,
		})
		if already_reversed:
			continue

		# Create negative reversal entry
		reversal = frappe.new_doc("Commission Entry")
		reversal.update({
			"sales_invoice": doc.name,  # Link to the credit note
			"company": orig.company,
			"customer": orig.customer,
			"commission_type": orig.commission_type,
			"commission_role": orig.commission_role,
			"commission_month": get_first_day(getdate(doc.posting_date)),
			"sales_person": orig.sales_person,
			"commission_pct": orig.commission_pct,
			"base_amount": -abs(flt(orig.base_amount)),  # Negative
			"manager": orig.manager,
			"manager_commission_pct": 0,
			"original_entry": orig.name,
			"status": "Pending",
		})
		reversal.flags.ignore_permissions = True
		reversal.flags.ignore_period_lock = True  # Reversals must bypass period lock
		reversal.insert()

		# Mark original as reversed
		frappe.db.set_value("Commission Entry", orig.name, {
			"status": "Reversed",
			"reversed_entry": reversal.name,
		})

	frappe.db.commit()


def _create_clawback_entry(entry, settings):
	"""
	For invoice cancellation when commission already paid:
	Create a reversal entry with negative amount and auto-create reversal JE.
	"""
	reversal = frappe.new_doc("Commission Entry")
	reversal.update({
		"sales_invoice": frappe.db.get_value("Commission Entry", entry.name, "sales_invoice"),
		"company": entry.company,
		"customer": entry.customer,
		"commission_type": entry.commission_type,
		"commission_role": entry.commission_role,
		"commission_month": get_first_day(getdate()),
		"sales_person": entry.sales_person,
		"commission_pct": entry.commission_pct,
		"base_amount": -abs(flt(entry.base_amount)),
		"manager": entry.manager,
		"manager_commission_pct": 0,
		"original_entry": entry.name,
		"status": "Paid",  # Auto-paid since it's a clawback
	})
	reversal.flags.ignore_permissions = True
	reversal.flags.ignore_period_lock = True  # Clawback must bypass period lock
	reversal.insert()

	# Auto-create reversal JE
	if (
		settings.auto_create_journal_entry
		and settings.commission_expense_account
		and settings.commission_payable_account
	):
		reversal_doc = frappe.get_doc("Commission Entry", reversal.name)
		reversal_doc._create_journal_entry(settings)

	# Mark original as reversed
	frappe.db.set_value("Commission Entry", entry.name, {
		"status": "Reversed",
		"reversed_entry": reversal.name,
	})

	frappe.msgprint(
		_("Clawback: Reversal entry {0} created for paid commission {1}").format(
			reversal.name, entry.name
		),
		indicator="orange",
	)


def _cancel_entries_for_invoice(invoice_name):
	"""Cancel all non-paid entries for an invoice (used when invoice is amended)."""
	entries = frappe.get_all(
		"Commission Entry",
		filters={"sales_invoice": invoice_name, "status": ["in", ["Pending", "Approved"]]},
		pluck="name",
	)
	for name in entries:
		frappe.db.set_value("Commission Entry", name, "status", "Cancelled")


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


def _get_tiered_rate(settings, sales_person, invoice_amount, posting_date):
	"""
	When tiered commission is enabled, calculate the rate based on
	cumulative monthly sales for this salesperson.
	Returns the tiered rate if matched, or None if no tier matches.
	"""
	if not settings.enable_tiered_commission:
		return None

	tiers = settings.get("commission_tiers") or []
	if not tiers:
		return None

	# Calculate cumulative sales this month for this salesperson
	month_start = get_first_day(getdate(posting_date))
	cumulative = frappe.db.sql("""
		SELECT COALESCE(SUM(st.allocated_amount), 0)
		FROM `tabSales Team` st
		JOIN `tabSales Invoice` si ON si.name = st.parent
		WHERE st.parenttype = 'Sales Invoice'
		AND st.sales_person = %s
		AND si.docstatus = 1
		AND si.is_return = 0
		AND si.posting_date >= %s
	""", (sales_person, month_start))[0][0]

	cumulative = flt(cumulative) + flt(invoice_amount)

	# Find matching tier
	for tier in sorted(tiers, key=lambda t: flt(t.from_amount)):
		to_amt = flt(tier.to_amount)
		if flt(tier.from_amount) <= cumulative and (to_amt == 0 or cumulative <= to_amt):
			return flt(tier.commission_pct)

	return None
