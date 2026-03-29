# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CommissionSettings(Document):
	# begin: auto-generated types
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from commission_engine.commission_engine.doctype.commission_rate_override.commission_rate_override import CommissionRateOverride

		auto_create_journal_entry: DF.Check
		commission_expense_account: DF.Link | None
		commission_payable_account: DF.Link | None
		commission_rate_overrides: DF.Table[CommissionRateOverride]
		enable_approval_workflow: DF.Check
		enable_tiered_commission: DF.Check
		maximum_commission_cap: DF.Currency
		minimum_commission_threshold: DF.Currency
		onetime_manager_pct: DF.Percent
		onetime_salesperson_pct: DF.Percent
		recurring_manager_pct: DF.Percent
		recurring_salesperson_pct: DF.Percent
	# end: auto-generated types

	def validate(self):
		self._validate_global_rates()
		self._validate_override_rates()
		self._check_duplicate_overrides()

	def _validate_global_rates(self):
		for field in [
			"onetime_salesperson_pct",
			"onetime_manager_pct",
			"recurring_salesperson_pct",
			"recurring_manager_pct",
		]:
			val = self.get(field)
			if val is not None and (val < 0 or val > 100):
				frappe.throw(
					frappe._(f"{self.meta.get_label(field)} must be between 0 and 100")
				)

	def _validate_override_rates(self):
		for row in self.commission_rate_overrides or []:
			for field in ["onetime_commission_pct", "recurring_commission_pct"]:
				val = row.get(field)
				if val is not None and val != 0 and (val < 0 or val > 100):
					frappe.throw(
						frappe._(
							f"Row #{row.idx}: {row.sales_person} — override rate must be between 0 and 100"
						)
					)

	def _check_duplicate_overrides(self):
		seen = set()
		for row in self.commission_rate_overrides or []:
			key = (row.sales_person, row.role)
			if key in seen:
				frappe.throw(
					frappe._(
						f"Row #{row.idx}: Duplicate override — {row.sales_person} as {row.role} "
						f"already exists. Remove the duplicate row."
					)
				)
			seen.add(key)
