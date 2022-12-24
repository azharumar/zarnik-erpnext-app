# Copyright (c) 2022, Zarnik Hotel Supplies Private Limited and contributors
# For license information, please see license.txt

import frappe
import pandas as pd

from erpnext.accounts.utils import get_balance_on

def test():
	pass

def execute(filters=None):

	pr = frappe.db.get_list("Payment Request",filters={"docstatus":1,"status":"Initiated","party_type":"Supplier"},fields=["name", "transaction_date", "payment_request_type", "party", "supplier_name", "reference_name", "grand_total", "status"])
	df = pd.DataFrame.from_records(pr)
	df['transaction_date'] = pd.to_datetime(df['transaction_date'])


	df["week"] = df['transaction_date'].dt.year.astype(str) + " - " + df['transaction_date'].dt.week.map("{:02}".format).astype(str)
	df = df.groupby(["party", "week", "supplier_name"],as_index=False)["grand_total"].sum()
	
	df = df.sort_values(by=['week'],ascending=True)
	df = df.pivot(index=["party","supplier_name"], columns='week', values='grand_total').reset_index().rename_axis(None, axis=1).fillna(0)

	df["Scheduled Total"] = round(df.iloc[:,1:].sum(axis=1),2)

	df["Ledger Balance"] = round(df.apply(lambda x: get_balance_on(party_type="Supplier",party=x['party']), axis=1),2)

	df["Unscheduled Amount"] = round(df["Ledger Balance"] + df["Scheduled Total"],2)
	df = df.set_index('party')
	df.rename(columns = {'party':'Supplier Code','supplier_name':'Supplier Name'}, inplace = True)

	data = df.values.tolist()
	columns = df.columns.values.tolist()
	print(columns)

	return columns, data
