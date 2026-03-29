# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Commission Entry"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Commission Entry",
			"width": 180,
		},
		{
			"label": _("Sales Person"),
			"fieldname": "sales_person",
			"fieldtype": "Link",
			"options": "Sales Person",
			"width": 160,
		},
		{
			"label": _("Person Name"),
			"fieldname": "sales_person_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Role"),
			"fieldname": "commission_role",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 140,
		},
		{
			"label": _("Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
		{
			"label": _("Commission Month"),
			"fieldname": "commission_month",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Commission Type"),
			"fieldname": "commission_type",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Invoice Amount"),
			"fieldname": "base_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Commission %"),
			"fieldname": "commission_pct",
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"label": _("Commission Amount"),
			"fieldname": "commission_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
	]


def get_data(filters):
	conditions, values = get_conditions(filters)

	entries = frappe.db.sql(
		"""
		SELECT
			ce.name,
			ce.sales_person,
			ce.sales_person_name,
			ce.commission_role,
			ce.customer,
			ce.customer_name,
			ce.sales_invoice,
			ce.commission_month,
			ce.commission_type,
			ce.base_amount,
			ce.commission_pct,
			ce.commission_amount,
			ce.status
		FROM `tabCommission Entry` ce
		WHERE ce.status NOT IN ('Cancelled')
		{conditions}
		ORDER BY ce.commission_month DESC, ce.sales_person
		""".format(conditions=conditions),
		values=values,
		as_dict=True,
	)

	return entries


def get_conditions(filters):
	conditions = []
	values = {}

	if filters.get("from_date"):
		conditions.append("AND ce.commission_month >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("AND ce.commission_month <= %(to_date)s")
		values["to_date"] = filters["to_date"]
	if filters.get("sales_person"):
		conditions.append("AND ce.sales_person = %(sales_person)s")
		values["sales_person"] = filters["sales_person"]
	if filters.get("commission_role"):
		conditions.append("AND ce.commission_role = %(commission_role)s")
		values["commission_role"] = filters["commission_role"]
	if filters.get("status"):
		conditions.append("AND ce.status = %(status)s")
		values["status"] = filters["status"]
	if filters.get("commission_type"):
		conditions.append("AND ce.commission_type = %(commission_type)s")
		values["commission_type"] = filters["commission_type"]
	if filters.get("company"):
		conditions.append("AND ce.company = %(company)s")
		values["company"] = filters["company"]

	return " ".join(conditions), values


def get_chart(data):
	if not data:
		return None

	sp_totals = {}
	for row in data:
		sp = row.get("sales_person_name") or row.get("sales_person")
		sp_totals[sp] = sp_totals.get(sp, 0) + flt(row.get("commission_amount"))

	sorted_sp = sorted(sp_totals.items(), key=lambda x: x[1], reverse=True)[:10]
	labels = [x[0] for x in sorted_sp]
	values = [x[1] for x in sorted_sp]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Commission"), "values": values}],
		},
		"type": "bar",
		"colors": ["#7cd6fd"],
		"title": _("Top Commission Earners"),
	}


def get_report_summary(data):
	sp_commission = sum(flt(r.get("commission_amount", 0)) for r in data if r.get("commission_role") == "Salesperson")
	mgr_commission = sum(flt(r.get("commission_amount", 0)) for r in data if r.get("commission_role") == "Manager")
	total_all = sum(flt(r.get("commission_amount", 0)) for r in data)
	pending = sum(flt(r.get("commission_amount", 0)) for r in data if r.get("status") == "Pending")
	approved = sum(flt(r.get("commission_amount", 0)) for r in data if r.get("status") == "Approved")

	return [
		{"value": sp_commission, "label": _("Salesperson Commission"), "datatype": "Currency", "indicator": "Green"},
		{"value": mgr_commission, "label": _("Manager Commission"), "datatype": "Currency", "indicator": "Blue"},
		{"value": total_all, "label": _("Grand Total"), "datatype": "Currency", "indicator": "Purple"},
		{"value": pending, "label": _("Pending"), "datatype": "Currency", "indicator": "Orange"},
		{"value": approved, "label": _("Approved (Awaiting Payment)"), "datatype": "Currency", "indicator": "Blue"},
	]
