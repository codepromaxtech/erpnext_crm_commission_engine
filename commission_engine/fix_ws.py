import frappe

def execute():
	try:
		workspace = frappe.get_doc("Workspace", "Commission Engine")
		# Check if already exists
		has_cf = any(link.label == "Customer Family" for link in workspace.links)
		if not has_cf:
			workspace.append("links", {
				"label": "Customer Family",
				"link_to": "Customer Family",
				"link_type": "DocType",
				"type": "Link",
				"onboard": 0
			})
			workspace.flags.ignore_permissions = True
			workspace.save(ignore_permissions=True)
			frappe.db.commit()
			print("Appended Customer Family to Workspace.")
		else:
			print("Customer Family already in Workspace.")
	except Exception as e:
		print("Error:", str(e))
