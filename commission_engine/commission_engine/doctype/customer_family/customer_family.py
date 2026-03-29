# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class CustomerFamily(Document):
	def validate(self):
		self._validate_unique_members()
		self._validate_primary_customer()

	def _validate_unique_members(self):
		"""Ensure no duplicate customers in the members table."""
		seen = set()
		for row in self.members or []:
			if row.customer in seen:
				frappe.throw(
					_("Row #{0}: Customer {1} is already listed in this family.").format(
						row.idx, row.customer
					)
				)
			seen.add(row.customer)

	def _validate_primary_customer(self):
		"""If primary_customer is set, ensure it's also in the members list."""
		if not self.primary_customer:
			return

		member_customers = [row.customer for row in self.members or []]
		if self.primary_customer not in member_customers:
			frappe.throw(
				_("Primary Customer {0} must also be listed in the Members table.").format(
					self.primary_customer
				)
			)
