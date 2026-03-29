# Copyright (c) 2026, CodeProMax Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_first_day, get_last_day, add_months, nowdate


@frappe.whitelist()
def bulk_mark_as_paid(names):
	"""Mark multiple Commission Entries as Paid."""
	import json
	if isinstance(names, str):
		names = json.loads(names)

	settings = frappe.get_cached_doc("Commission Settings")
	count = 0
	for name in names:
		doc = frappe.get_doc("Commission Entry", name)
		# Allow Pending→Paid only if approval is disabled, or already Approved
		if doc.status in ("Pending", "Approved"):
			if doc.status == "Pending" and settings.enable_approval_workflow:
				continue  # Must be approved first
			doc.status = "Paid"
			doc.flags.ignore_permissions = True
			doc.save()
			count += 1

	frappe.db.commit()
	return {"message": _("{0} commission entries marked as Paid").format(count), "count": count}


@frappe.whitelist()
def bulk_approve(names):
	"""Approve multiple Pending Commission Entries."""
	import json
	if isinstance(names, str):
		names = json.loads(names)

	count = 0
	for name in names:
		doc = frappe.get_doc("Commission Entry", name)
		if doc.status == "Pending":
			doc.status = "Approved"
			doc.flags.ignore_permissions = True
			doc.save()
			count += 1

	frappe.db.commit()
	return {"message": _("{0} commission entries approved").format(count), "count": count}



@frappe.whitelist()
def get_commission_dashboard(company=None):
	"""Return dashboard data for the Commission Engine workspace."""
	filters = {"status": ["!=", "Cancelled"]}
	if company:
		filters["company"] = company

	entries = frappe.get_all(
		"Commission Entry",
		filters=filters,
		fields=[
			"name", "status", "commission_type", "commission_amount",
			"commission_role", "base_amount", "commission_month",
			"sales_person", "sales_person_name", "manager", "manager_name",
		],
	)

	today = getdate(nowdate())
	this_month_start = get_first_day(today)
	last_month_start = get_first_day(add_months(today, -1))
	last_month_end = get_last_day(add_months(today, -1))

	# Summary totals
	total_commission = sum(flt(e.commission_amount) for e in entries)
	total_pending = sum(
		flt(e.commission_amount)
		for e in entries if e.status == "Pending"
	)
	total_paid = sum(
		flt(e.commission_amount)
		for e in entries if e.status == "Paid"
	)

	# This month
	this_month_entries = [e for e in entries if e.commission_month and getdate(e.commission_month) >= this_month_start]
	this_month_total = sum(flt(e.commission_amount) for e in this_month_entries)

	# Last month
	last_month_entries = [
		e for e in entries
		if e.commission_month and last_month_start <= getdate(e.commission_month) <= last_month_end
	]
	last_month_total = sum(flt(e.commission_amount) for e in last_month_entries)

	# Top 5 salespersons
	sp_totals = {}
	for e in entries:
		sp = e.sales_person_name or e.sales_person
		sp_totals[sp] = sp_totals.get(sp, 0) + flt(e.commission_amount)
	top_salespersons = sorted(sp_totals.items(), key=lambda x: x[1], reverse=True)[:5]

	# Monthly trend (last 6 months)
	monthly_trend = {}
	for e in entries:
		if e.commission_month:
			month_key = str(get_first_day(getdate(e.commission_month)))
			monthly_trend[month_key] = monthly_trend.get(month_key, 0) + flt(e.commission_amount)

	sorted_months = sorted(monthly_trend.items())[-6:]

	# One-Time vs Recurring split
	onetime_total = sum(
		flt(e.commission_amount)
		for e in entries if e.commission_type == "One-Time"
	)
	recurring_total = sum(
		flt(e.commission_amount)
		for e in entries if e.commission_type == "Recurring"
	)

	return {
		"total_entries": len(entries),
		"total_commission": total_commission,
		"total_pending": total_pending,
		"total_paid": total_paid,
		"this_month_total": this_month_total,
		"last_month_total": last_month_total,
		"this_month_entries": len(this_month_entries),
		"top_salespersons": [{"name": s[0], "total": s[1]} for s in top_salespersons],
		"monthly_trend": [{"month": m[0], "total": m[1]} for m in sorted_months],
		"onetime_total": onetime_total,
		"recurring_total": recurring_total,
	}
