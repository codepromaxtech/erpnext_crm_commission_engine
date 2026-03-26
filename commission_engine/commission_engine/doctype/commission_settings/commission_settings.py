# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CommissionSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auto_create_journal_entry: DF.Check
		commission_expense_account: DF.Link | None
		commission_payable_account: DF.Link | None
		onetime_manager_pct: DF.Percent
		onetime_salesperson_pct: DF.Percent
		recurring_manager_pct: DF.Percent
		recurring_salesperson_pct: DF.Percent
	# end: auto-generated types

	def validate(self):
		for field in [
			"onetime_salesperson_pct",
			"onetime_manager_pct",
			"recurring_salesperson_pct",
			"recurring_manager_pct",
		]:
			if self.get(field) < 0 or self.get(field) > 100:
				frappe.throw(
					frappe._(f"{self.meta.get_label(field)} must be between 0 and 100")
				)
