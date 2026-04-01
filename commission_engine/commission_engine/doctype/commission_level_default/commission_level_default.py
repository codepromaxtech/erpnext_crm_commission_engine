# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING
from frappe.model.document import Document

if TYPE_CHECKING:
	from frappe.types import DF

	hierarchy_level: DF.Int
	level_title: DF.Data | None
	onetime_pct: DF.Percent
	parent: DF.Data
	parentfield: DF.Data
	parenttype: DF.Data

class CommissionLevelDefault(Document):
	pass
