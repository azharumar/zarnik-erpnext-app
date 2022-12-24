# Copyright (c) 2022, Zarnik Hotel Supplies Private Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate

def execute(filters=None):
	if not filters:
		return [], [], None, []

	validate_filters(filters)

	columns = get_columns(filters)
	conditions = get_conditions(filters)
	data = get_data(conditions, filters)

	if not data:
		return [], [], None, []

	# data, chart_data = prepare_data(data, filters)

	return columns, data

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

def get_conditions(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " and so.transaction_date between %(from_date)s and %(to_date)s"

	if filters.get("company"):
		conditions += " and so.company = %(company)s"

	if filters.get("sales_order"):
		conditions += " and so.name in %(sales_order)s"

	if filters.get("status"):
		conditions += " and so.status = %(status)s"

	return conditions

def get_data(conditions, filters):
	data = frappe.db.sql("""
		SELECT
			so.name as sales_order,
			so.status, 
   			so.customer_name, 
   			soi.item_code,
   			soi.item_name,
   			soi.description as idesc,
   			soi.additional_notes as ian,
   			soi.item_comments as isc,
   			so.order_comments as soc,
			soi.qty,
   			(soi.qty - soi.delivered_qty) AS pending_qty,
			DATEDIFF(CURDATE(), soi.delivery_date) as delay_days,
			IF(so.status in ('Completed','To Bill'), 0, (SELECT delay_days)) as delay,
   			soi.delivery_date as delivery_date,
			soi.warehouse as warehouse,
			(soi.billed_amt * IFNULL(so.conversion_rate, 1)) as billed_amount,
			(soi.base_amount - (soi.billed_amt * IFNULL(so.conversion_rate, 1))) as pending_amount,
			so.company
		FROM
			`tabSales Order` so,
			`tabSales Order Item` soi
		LEFT JOIN `tabSales Invoice Item` sii
			ON sii.so_detail = soi.name and sii.docstatus = 1
		WHERE
			soi.parent = so.name
			and so.status not in ('Stopped', 'Closed', 'On Hold')
			and so.docstatus = 1
			{conditions}
		GROUP BY soi.name
		HAVING pending_qty>0
		ORDER BY so.transaction_date ASC
	""".format(conditions=conditions), filters, as_dict=1)

	return data

def prepare_data(data, filters):
	completed, pending = 0, 0

	if filters.get("group_by_so"):
		sales_order_map = {}

	# for row in data:
		# sum data for chart
		# completed += row["billed_amount"]
		# pending += row["pending_amount"]

		# prepare data for report view
		# row["qty_to_bill"] = flt(row["qty"]) - flt(row["billed_qty"])

		# row["delay"] = 0 if row["delay"] and row["delay"] < 0 else row["delay"]
		# if filters.get("group_by_so"):
		# 	so_name = row["sales_order"]

		# 	if not so_name in sales_order_map:
		# 		# create an entry
		# 		row_copy = copy.deepcopy(row)
		# 		sales_order_map[so_name] = row_copy
		# 	else:
		# 		# update existing entry
		# 		so_row = sales_order_map[so_name]
		# 		so_row["required_date"] = max(getdate(so_row["delivery_date"]), getdate(row["delivery_date"]))
		# 		so_row["delay"] = min(so_row["delay"], row["delay"])

		# 		# sum numeric columns
		# 		fields = ["qty", "delivered_qty", "pending_qty", "billed_qty", "qty_to_bill", "amount",
		# 			"delivered_qty_amount", "billed_amount", "pending_amount"]
		# 		for field in fields:
		# 			so_row[field] = flt(row[field]) + flt(so_row[field])

	# chart_data = prepare_chart_data(pending, completed)

	# if filters.get("group_by_so"):
	# 	data = []
	# 	for so in sales_order_map:
	# 		data.append(sales_order_map[so])
	# 	return data, chart_data

	return data

def prepare_chart_data(pending, completed):
	labels = ["Amount to Bill", "Billed Amount"]

	return {
		"data" : {
			"labels": labels,
			"datasets": [
				{"values": [pending, completed]}
				]
		},
		"type": 'donut',
		"height": 300
	}

def get_columns(filters):
	columns = [
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 120
		},
# 		{
#			"label":_("Status"),
#			"fieldname": "status",
#			"fieldtype": "Data",
#			"width": 130
#		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 300
		},
#  		{
#			"label":_("Item Code"),
#			"fieldname": "item_code",
#			"fieldtype": "Link",
#			"options": "Item",
#			"width": 100
#		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "data",
			"width": 300
		},
#  		{
#			"label": _("Item Additional Notes"),
#			"fieldname": "ian",
#			"fieldtype": "data",
#			"width": 180
#		},
#   	{
#			"label": _("Item Status Comments"),
#			"fieldname": "isc",
#			"fieldtype": "data",
#			"width": 180
#		},
#		{
#			"label": _("Order Qty"),
#			"fieldname": "qty",
#			"fieldtype": "Float",
#			"width": 120,
#			"convertible": "qty"
#		},
		{
			"label": _("Qty to Deliver"),
			"fieldname": "pending_qty",
			"fieldtype": "Float",
			"width": 120,
			"convertible": "qty"
		},
#		{
#			"label":_("Delivery Date"),
#			"fieldname": "delivery_date",
#			"fieldtype": "Date",
#			"width": 120
#		},
		{
			"label": _("Delay"),
			"fieldname": "delay",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": _("Sales Order Comments"),
			"fieldname": "soc",
			"fieldtype": "data",
			"editable": True,
			"width": 300
		},
#  		{
#			"label": _("Warehouse"),
#			"fieldname": "warehouse",
#			"fieldtype": "Link",
#			"options": "Warehouse",
#			"width": 100
#		},
#   	{
#			"label": _("Company"),
#			"fieldname": "company",
#			"fieldtype": "Link",
#			"options": "Company",
#			"width": 100
#		}
	]


	return columns
