# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, get_first_day, getdate


class CommissionPeriod(Document):
	def validate(self):
		# Ensure period_month is always first day of month
		self.period_month = get_first_day(getdate(self.period_month))

	def on_update(self):
		if self.has_value_changed("period_status"):
			if self.period_status == "Locked":
				self.db_set("locked_by", frappe.session.user)
				self.db_set("locked_date", now())
				self._refresh_summary()
				frappe.msgprint(
					_("Commission period {0} has been locked. No entries can be modified.").format(
						self.period_month),
					indicator="red"
				)
			elif self.period_status == "Open":
				self.db_set("locked_by", None)
				self.db_set("locked_date", None)

	def _refresh_summary(self):
		"""Update summary stats for this period."""
		entries = frappe.get_all(
			"Commission Entry",
			filters={
				"commission_month": self.period_month,
				"status": ["not in", ["Cancelled"]],
			},
			fields=["commission_amount", "status"],
		)
		self.db_set("total_entries", len(entries))
		self.db_set("total_commission", sum(flt(e.commission_amount) for e in entries))
		self.db_set("total_paid", sum(
			flt(e.commission_amount) for e in entries if e.status == "Paid"
		))


def is_period_locked(commission_month):
	"""Check if a commission period is locked."""
	period_month = get_first_day(getdate(commission_month))
	period = frappe.db.get_value(
		"Commission Period",
		{"period_month": period_month, "period_status": "Locked"},
		"name",
	)
	return bool(period)
