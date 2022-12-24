import frappe
from frappe.utils import today, add_to_date

import erpnext
from erpnext.stock.utils import get_latest_stock_qty, get_stock_value_on

import pandas as pd
from openpyxl import load_workbook

import numpy as np
from numpy import inf


def disable_inactive_items():
    for items in frappe.db.get_list("Item",{"is_stock_item":1,"is_fixed_asset":0,"disabled":0},["item_code"]):
        stock_qty = erpnext.stock.utils.get_latest_stock_qty(items.item_code, warehouse=None)
        if stock_qty == 0:
            stock_value = get_stock_value_on(warehouse=None, posting_date=None, item_code=items.item_code)
            if stock_value == 0:
                if not frappe.db.get_list("Stock Ledger Entry",{"item_code":items.item_code, "posting_date":["between",[add_to_date(today(), days=-90, as_string=True),today()]], "voucher_type":["!=","Stock Reconciliation"]}):
                    frappe.db.set_value("Item",{"name":items.item_code},{"disabled":1})
                    print(items.item_code)

def is_outlier(x): 
    IQR = np.percentile(x, 75) - np.percentile(x, 25)
    upper_fence = np.percentile(x, 75) + (IQR * 1.5)
    lower_fence = np.percentile(x, 25) - (IQR * 1.5)
    return (x > upper_fence) | (x < lower_fence)

def set_reorder_values():

    #### Reset reorder values ####
    for warehouse in frappe.db.get_list("Warehouse", filters = {"is_group":0},fields=["warehouse_name"]):
        for item in frappe.db.get_list("Item",filters={"disabled":0,"is_stock_item":1,"is_fixed_asset":0}):
            request_type = "Purchase"
            bom = frappe.db.get_value("BOM", {"item": item.name, "is_active": 1, "is_default": 1})
            if bom:
                request_type = "Manufacture"
            item_reorder = frappe.db.get_value("Item Reorder",{"parent":item.name,"warehouse":frappe.db.get_value("Warehouse",{"warehouse_name":warehouse.warehouse_name})})
            if item_reorder:
                frappe.db.set_value("Item Reorder",{"parent":item.name,"warehouse":frappe.db.get_value("Warehouse",{"warehouse_name":warehouse.warehouse_name})},{
                    "warehouse_reorder_level":0,
                    "warehouse_reorder_qty":1,
                    "material_request_type":str(request_type),
                })
            else:
                doc = frappe.get_doc("Item",item.get("name"))
                doc.append("reorder_levels",{
                    "warehouse":frappe.db.get_value("Warehouse",{"warehouse_name":warehouse.warehouse_name}),
                    "warehouse_reorder_level":0,
                    "warehouse_reorder_qty":1,
                    "material_request_type":str(request_type),
                })
                doc.save()

    pd.set_option('use_inf_as_na', True)

    path = "/home/frappe/frappe-bench/apps/inventory_management/inventory_management/reorder_level_workings.xlsx" 

    d1 = add_to_date(today(), days=-90, as_string=True)
    d2 = today()

    data_item = frappe.db.get_list("Item",{"is_stock_item":1,"is_fixed_asset":0},["item_code", "item_name", "moq", "order_multiple"])
    df_item = pd.DataFrame.from_records(data_item)

    data_sales_invoice = frappe.db.get_list("Sales Invoice",{"docstatus":1,"posting_date":["between",[d1,d2]]},["name","posting_date"])
    df_sales_invoice = pd.DataFrame.from_records(data_sales_invoice)

    data_sales_invoice_item = frappe.db.get_list("Sales Invoice Item",{"docstatus":1,"stock_qty":[">",0],"net_amount":[">",0],"item_code":["not like","%NON-STOCK%"]},["parent","item_code","warehouse","stock_qty","net_amount"])
    df_data_sales_invoice_item = pd.DataFrame.from_records(data_sales_invoice_item)

    df_data_sales_invoice_item = pd.merge(df_data_sales_invoice_item, df_item, how="left", left_on="item_code", right_on="item_code")
    df_demand = pd.merge(df_sales_invoice, df_data_sales_invoice_item, how="left", left_on="name", right_on="parent")
    df_demand["posting_date"] = pd.to_datetime(df_demand["posting_date"])
    df_demand = df_demand.drop(["parent"], axis=1)
    df_demand = df_demand.dropna()

    with pd.ExcelWriter(path) as writer: 
        df_demand.to_excel(writer, sheet_name='df_demand_before_outlier_filter')

    df_demand = df_demand[~df_demand.groupby(['item_code', 'warehouse'])['stock_qty'].apply(is_outlier)]
    df_demand = df_demand.groupby(["item_code","warehouse"]).filter(lambda x : len(x)>2)

    df_demand.to_excel(writer, sheet_name='df_demand_after_outlier_filter')

    # Getting BOM data
    data_bom_item = frappe.db.get_list("BOM Item",{"stock_qty":[">",0]},["parent", "item_code", "stock_qty"])
    df_bom_item = pd.DataFrame.from_records(data_bom_item)

    data_bom = frappe.db.get_list("BOM",{"is_active":1,"is_default":1},["name", "item", "quantity"])
    df_bom = pd.DataFrame.from_records(data_bom)

    df_bom = pd.merge(df_bom[["name", "item", "quantity"]], df_bom_item[["parent", "item_code", "stock_qty"]], how="left", left_on="name", right_on="parent")
    df_bom["qty_per_unit"] = df_bom["quantity"] * df_bom["stock_qty"]

    df_bom = df_bom.drop(["name", "parent", "quantity", "stock_qty"], axis=1)
    df_bom = df_bom.rename(columns={"item": "parent_item", "item_code": "child_item"})

    df_bom = pd.merge(df_demand,df_bom, how="left", left_on="item_code", right_on="parent_item")
    df_bom = df_bom[df_bom.parent_item.notnull()]
    df_bom = df_bom.drop(["item_code", "parent_item","qty_per_unit", "item_name"], axis=1)
    df_bom = df_bom.rename(columns={"child_item":"item_code"})
    df_bom = pd.merge(df_bom, df_item, how="left", left_on="item_code", right_on="item_code")

    df_demand = pd.concat([df_demand, df_bom])

    ###### ABC Analysis ######
    df_abc = df_demand.assign()
    df_abc = df_abc.groupby(["item_code", "warehouse"],as_index=False)["net_amount","stock_qty"].sum()
    df_abc["percent"] = ((df_abc["net_amount"]/df_abc["net_amount"].sum())*100)
    df_abc = df_abc.sort_values(by="percent", ascending=False)
    df_abc["cum_percent"] = df_abc["percent"].cumsum()
    df_abc.loc[df_abc["cum_percent"] > 90, "ABC"] = "C"
    df_abc.loc[df_abc["cum_percent"] < 90, "ABC"] = "B"
    df_abc.loc[df_abc["cum_percent"] < 60, "ABC"] = "A"

    df_abc.to_excel(writer, sheet_name='df_abc')

    ###### XYZ Analysis ######
    df_xyz = df_demand.assign()
    df_xyz["weeknum"] = df_xyz["posting_date"].dt.week
    df_xyz = df_xyz.groupby(["item_code", "warehouse", "weeknum"],as_index=False)["stock_qty"].sum()
    df_xyz_weeks = df_xyz["weeknum"].max() - df_xyz["weeknum"].min()

    df_xyz_mean_qty = (df_xyz.groupby(["item_code", "warehouse"])["stock_qty"].sum()/df_xyz_weeks).rename("mean_qty").reset_index() 
    df_xyz_std_qty = df_xyz.groupby(["item_code", "warehouse"])["stock_qty"].std().rename("std_qty").reset_index()
    df_xyz = df_xyz.merge(df_xyz_mean_qty)
    df_xyz = df_xyz.merge(df_xyz_std_qty)

    df_xyz = pd.merge(df_xyz, df_item[["item_code", "order_multiple"]], how="left", left_on="item_code", right_on="item_code")
    df_xyz = df_xyz[df_xyz["mean_qty"] >= df_xyz["order_multiple"]]

    df_xyz["coeff_var"] = ((df_xyz["std_qty"]/df_xyz["mean_qty"])*100)

    df_xyz.sort_values(by=["weeknum"])

    df_xyz_range = (df_xyz["coeff_var"].max() - df_xyz["coeff_var"].min()) / 3
    df_xyz_cluster_1 = df_xyz["coeff_var"].min() + df_xyz_range
    df_xyz_cluster_2 = df_xyz_cluster_1 + df_xyz_range

    df_xyz.loc[df_xyz["coeff_var"] < df_xyz_cluster_1, "XYZ"] = "X"
    df_xyz.loc[df_xyz["coeff_var"] > df_xyz_cluster_1, "XYZ"] = "Y"
    df_xyz.loc[df_xyz["coeff_var"] > df_xyz_cluster_2, "XYZ"] = "Z"
    df_xyz.loc[df_xyz["mean_qty"] < 1, "XYZ"] = "Z"
    df_xyz.loc[df_xyz["std_qty"].isnull(), "XYZ"] = "Z"
    
    df_xyz = df_xyz.drop_duplicates(subset=["item_code", "warehouse"])
    df_xyz = df_xyz.drop(["weeknum"], axis=1)

    df_xyz = df_xyz.sort_values(by="XYZ", ascending=True)

    df_xyz.to_excel(writer, sheet_name='df_xyz')

    #Merge ABC and XYX Dataframes

    df_abc_xyz = pd.merge(df_abc[["item_code", "warehouse", "ABC"]], df_xyz[["item_code", "warehouse", "XYZ", "mean_qty", "std_qty"]])

    df_abc_xyz["ABC_XYZ"] = df_abc_xyz["ABC"] + df_abc_xyz["XYZ"]
    df_abc_xyz = df_abc_xyz.groupby(["item_code", "warehouse", "ABC_XYZ"],as_index=False).mean()
    #df_abc_xyz = df_abc_xyz.drop(["ABC", "XYZ"], axis=1)

    # Assign service levsl to ABC-XYZ
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "AX", "service_level"] = 0.9
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "AY", "service_level"] = 0.85
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "AZ", "service_level"] = 0.8
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "BX", "service_level"] = 0.75
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "BY", "service_level"] = 0.7
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "BZ", "service_level"] = 0.65
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "CX", "service_level"] = 0.6
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "CY", "service_level"] = 0.55
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "CZ", "service_level"] = 0.5

    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "AX", "z_factor"] = 1.28
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "AY", "z_factor"] = 1.04
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "AZ", "z_factor"] = 0.84
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "BX", "z_factor"] = 0.67
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "BY", "z_factor"] = 0.52
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "BZ", "z_factor"] = 0.39
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "CX", "z_factor"] = 0.25
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "CY", "z_factor"] = 0.13
    df_abc_xyz.loc[df_abc_xyz["ABC_XYZ"] == "CZ", "z_factor"] = 0

    df_abc_xyz = df_abc_xyz.sort_values(by="ABC_XYZ", ascending=True)

    df_abc_xyz.to_excel(writer, sheet_name='df_abc_xyz')

    ###### Lead Time ######
    # Get Purchase Order, Purchase Invoice and Purchase Invoice Item from ERPNext Database
    purchase_order = frappe.db.get_list("Purchase Order",{"docstatus":1,"transaction_date":["between",[add_to_date(today(), days=-90, as_string=True),today()]]},["name","transaction_date"])
    purchase_invoice = frappe.db.get_list("Purchase Invoice",{"docstatus":1,"posting_date":["between",[add_to_date(today(), days=-90, as_string=True),today()]]},["name","posting_date"])
    purchase_invoice_item = frappe.db.get_list("Purchase Invoice Item",{"docstatus":1, "is_fixed_asset":0, "item_code":["not like","%NON-STOCK%"]},["parent","item_code","warehouse","purchase_order"])

    df_purchase_order = pd.DataFrame.from_records(purchase_order)
    df_purchase_order = df_purchase_order.rename(columns={"name": "purchase_order", "transaction_date": "purchase_order_date"})
    df_purchase_order["purchase_order_date"] = pd.to_datetime(df_purchase_order["purchase_order_date"])

    df_purchase_invoice = pd.DataFrame.from_records(purchase_invoice)
    df_purchase_invoice = df_purchase_invoice.rename(columns={"name":"purchase_invoice", "posting_date":"purchase_invoice_date"})
    df_purchase_invoice["purchase_invoice_date"] = pd.to_datetime(df_purchase_invoice["purchase_invoice_date"])

    df_purchase_invoice_item = pd.DataFrame.from_records(purchase_invoice_item)
    df_purchase_invoice_item = df_purchase_invoice_item.rename(columns={"parent":"purchase_invoice"})
    
    # Merge Purchase Order, Purchase Invoice and Purchase Invoice | Filter out rows without PO Date or PI Date
    df_lead_time = pd.merge(df_purchase_invoice_item, df_purchase_invoice, how="left", left_on="purchase_invoice", right_on="purchase_invoice")
    df_lead_time = pd.merge(df_lead_time, df_purchase_order, how="left", left_on="purchase_order", right_on="purchase_order")
    df_lead_time = df_lead_time[df_lead_time["purchase_invoice_date"] > add_to_date(today(), days=-90, as_string=True)]
    df_lead_time = df_lead_time[df_lead_time["purchase_order_date"] > add_to_date(today(), days=-90, as_string=True)]

    # Calculate Lead Time, Avergae Lead Time and Lead Time Standard Deviation
    df_lead_time["lt"] = (df_lead_time["purchase_invoice_date"] - df_lead_time["purchase_order_date"]).dt.days + 1
    df_lt_mean = (df_lead_time.groupby(["item_code", "warehouse"])["lt"].mean()/7).rename("lt_mean").reset_index()#.fillna(0)
    df_lt_std = (df_lead_time.groupby(["item_code", "warehouse"])["lt"].std()/7).rename("lt_std").reset_index().fillna(0)
    df_lead_time = df_lead_time.merge(df_lt_mean)
    df_lead_time = df_lead_time.merge(df_lt_std)
    df_lead_time = df_lead_time.groupby(["item_code", "warehouse","lt_mean", "lt_std"],as_index=False).count()
    df_lead_time = df_lead_time.drop(["purchase_invoice", "purchase_order","purchase_invoice_date", "purchase_order_date", "lt"], axis=1)

    df_lead_time = pd.merge(df_abc_xyz, df_lead_time, how="left", on=["item_code", "warehouse"])

    df_lead_time.loc[df_lead_time["lt_mean"].isnull(), "lt_mean"] = 1
    df_lead_time.loc[df_lead_time["lt_std"].isnull(), "lt_std"] = 0

    df_lead_time.to_excel(writer, sheet_name='df_lead_time')

    # Calculate Safety Stock and Reorder Point
    df_reorder =  df_lead_time.assign()

    df_reorder["safety_stock"] = (((df_lead_time["lt_mean"] * (df_reorder["std_qty"].pow(2))) + (df_reorder["lt_std"].pow(2) * df_reorder["mean_qty"].pow(2))).pow(1./2)) * df_reorder["z_factor"]
    df_reorder.loc[df_reorder["safety_stock"] < 1, "safety_stock"] = 0
    df_reorder.loc[df_reorder["safety_stock"].isnull(), "safety_stock"] = 0
    df_reorder["safety_stock"] = df_reorder["safety_stock"].round()

    df_reorder["reorder_point"] = df_reorder["safety_stock"] + (df_reorder["lt_mean"] * df_reorder["mean_qty"])
    df_reorder.loc[df_reorder["safety_stock"] < 1, "reorder_point"] = 0
    df_reorder.loc[df_reorder["safety_stock"].isnull(), "reorder_point"] = 0
    df_reorder["reorder_point"] = df_reorder["reorder_point"].round()

    df_reorder = pd.merge(df_reorder, df_item, how="left", left_on="item_code", right_on="item_code")
    df_reorder = df_reorder[["item_code", "item_name", "warehouse", "ABC_XYZ", "mean_qty", "std_qty", "service_level", "z_factor", "lt_mean", "lt_std", "safety_stock", "reorder_point"]]

    df_reorder.to_excel(writer, sheet_name='df_reorder')

    #Calculate EOQ
    data_stock_entry = frappe.db.get_list("Stock Ledger Entry",{"docstatus":1,"posting_date":["between",[add_to_date(today(), days=-90, as_string=True),today()]]},["posting_date", "item_code", "warehouse", "valuation_rate"])
    df_stock_entry = pd.DataFrame.from_records(data_stock_entry)
    df_stock_entry["posting_date"] = pd.to_datetime(df_stock_entry["posting_date"])
    df_stock_entry = df_stock_entry.sort_values(by="posting_date")
    df_stock_entry = df_stock_entry.drop_duplicates(["item_code","warehouse"], keep="last")
    df_stock_entry = df_stock_entry.drop(["posting_date"], axis=1)

    df_stock_entry.to_excel(writer, sheet_name='df_stock_entry')
    
    TC = 100            ## Ordering cost at Rs. 100
    HC = .1             ## Holding cost at 10%

    df_eoq = df_reorder[["item_code", "item_name", "warehouse", "mean_qty", "safety_stock", "reorder_point"]].copy()
    df_eoq = pd.merge(df_eoq, df_stock_entry, how="left", left_on=["item_code", "warehouse"], right_on=["item_code", "warehouse"])
    df_eoq["eoq"] = ((2 * TC * df_eoq["mean_qty"])/(df_eoq["valuation_rate"] * HC)).pow(1./2)
    df_eoq["eoq"] = df_eoq["eoq"].round()
    df_eoq = df_eoq.fillna(0)

    df_eoq.to_excel(writer, sheet_name='df_eoq')
    
    for row in df_eoq.index:
        frappe.db.set_value("Item Reorder",{"parent":df_eoq["item_code"][row],"warehouse":df_eoq["warehouse"][row]},{"warehouse_reorder_level":df_eoq["reorder_point"][row], "warehouse_reorder_qty":df_eoq["eoq"][row]})

    print("Done")

    writer.save()

def create_purchase_orders():

    ## Creates purchase orders against generated material requests ##

    date_item = frappe.db.get_list("Item",["item_code", "min_order_qty","order_multiple"])
    df_item = pd.DataFrame.from_records(date_item)
    
    data_item_reorder = frappe.db.get_list("Item Reorder",["parent", "warehouse","supplier"])
    df_item_reorder = pd.DataFrame.from_records(data_item_reorder)
    df_item_reorder = df_item_reorder.rename({"parent":"item_code"}, axis=1)

    data_mr_item = frappe.db.get_list("Material Request Item",{"docstatus":1},["parent", "item_code", "warehouse","stock_qty"])
    df_mr_item = pd.DataFrame.from_records(data_mr_item)

    data_mr = frappe.db.get_list("Material Request",{"docstatus":1},["name", "status", "material_request_type"])
    df_mr = pd.DataFrame.from_records(data_mr)

    df_to_order = pd.merge(df_mr_item, df_mr, how="left", left_on="parent", right_on="name")
    df_to_order = df_to_order.drop(["name", "parent"], axis=1)
    df_to_order = df_to_order[df_to_order["status"] == "Pending"]
    df_to_order = df_to_order.groupby(["item_code", "warehouse", "material_request_type"])["stock_qty"].sum()

    df_to_order = pd.merge(df_to_order, df_item_reorder, how="left", left_on=["item_code", "warehouse"], right_on=["item_code", "warehouse"])
    df_to_order = pd.merge(df_to_order, df_item, how="inner", left_on=["item_code"], right_on=["item_code"])

    df_to_order.loc[df_to_order["stock_qty"] <= df_to_order["min_order_qty"], "po_qty"] = df_to_order["min_order_qty"]
    df_to_order.loc[df_to_order["stock_qty"] >= df_to_order["min_order_qty"], "po_qty"] = df_to_order["stock_qty"]

    df_to_order["po_qty"] = (df_to_order["po_qty"]/df_to_order["order_multiple"]).apply(np.ceil) * df_to_order["order_multiple"]

    print(df_to_order.to_string())

    
