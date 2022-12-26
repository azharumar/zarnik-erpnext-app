import frappe
from frappe.utils import now
from frappe.utils import nowdate

from pathlib import Path

from zarnik.ap_automation.razorpay_api import payout_composite_bank_account
from zarnik.ap_automation.razorpay_api import fetch_transaction_by_id

import time

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

def schedule_payment_requests(doc, method):
    if doc.enable_automatic_payment == 1:
        for line in doc.get("payment_schedule"):
            pr = frappe.get_doc({"doctype":"Payment Request"})
            pr.payment_request_type = "Outward"
            pr.transaction_date = line.get("due_date")
            pr.party_type = "Supplier"
            pr.party = doc.get("supplier")
            pr.reference_doctype = doc.doctype
            pr.reference_name = doc.get("name")
            pr.grand_total = line.get("payment_amount")
            pr.bank_account = frappe.db.get_value("Bank Account",{"account_name":"DUMMY"})
            pr.mode_of_payment = frappe.db.get_value("Mode of Payment",{"name":"Bank Transfer (API)"})
            pr.save()
            pr.submit()

def create_payment_orders_weekly():
    for party_list in frappe.db.get_list("Payment Request",fields=["party"],filters=[["Status","=","Initiated"],["transaction_date","<=",frappe.utils.nowdate()],["payment_request_type","=","Outward"], ["reference_doctype","=","Purchase Invoice"],["hold","=",0]],group_by="party"):
        doc = frappe.get_doc({
            "doctype":"Payment Order",
            "payment_order_type":"Payment Request",
            "party":party_list.party,
            "company_bank_account":frappe.db.get_value("Bank Account",{"is_automatic_payout_account":1},"name"),
            })
        for payment_request in frappe.db.get_list("Payment Request",fields=["name","party","reference_doctype","reference_name","grand_total","bank_account"],filters=[["Status","=","Initiated"],["transaction_date","<",frappe.utils.nowdate()],["payment_request_type","=","Outward"],["party","=",party_list.party]]):
            doc.append("references",{
                "reference_doctype":payment_request.reference_doctype,
                "reference_name":payment_request.reference_name,
                "amount":payment_request.grand_total,
                "supplier": frappe.db.get_value("Supplier",{"name":payment_request.party}),
                "payment_request":payment_request.name,
                "bank_account":payment_request.bank_account
                })
        bank_details = frappe.db.get_value ("Supplier",{"name":doc.party},["account_name","bank_account_number","ifsc", "contact_name", "mobile", "email"],as_dict=True)
        doc.account_name = bank_details.account_name
        doc.account_number = bank_details.bank_account_number
        doc.branch_code = bank_details.ifsc
        doc.contact_name = bank_details.contact_name
        doc.email = bank_details.email
        doc.mobile = bank_details.mobile
        doc.total_amount = 0
        amount = 0
        for line in doc.get("references"):
            amount = line.amount
            doc.total_amount = amount + doc.total_amount
        doc.save()
        doc.submit()


def create_payment_orders_hourly():
    for party_list in frappe.db.get_list("Payment Request",fields=["party"],filters=[["Status","=","Initiated"],["transaction_date","=",frappe.utils.nowdate()],["payment_request_type","=","Outward"], ["reference_doctype","=","Purchase Order"],["hold","=",0]],group_by="party"):
        doc = frappe.get_doc({
            "doctype":"Payment Order",
            "payment_order_type":"Payment Request",
            "party":party_list.party,
            "company_bank_account":frappe.db.get_value("Bank Account",{"is_automatic_payout_account":1},"name"),
            })
        for payment_request in frappe.db.get_list("Payment Request",fields=["name","party","reference_doctype","reference_name","grand_total","bank_account"],filters=[["Status","=","Initiated"],["transaction_date","=",frappe.utils.nowdate()],["payment_request_type","=","Outward"],["party","=",party_list.party],["reference_doctype","=","Purchase Order"]]):
            doc.append("references",{
                "reference_doctype":payment_request.reference_doctype,
                "reference_name":payment_request.reference_name,
                "amount":payment_request.grand_total,
                "supplier": frappe.db.get_value("Supplier",{"name":payment_request.party}),
                "payment_request":payment_request.name,
                "bank_account":payment_request.bank_account
                })
        bank_details = frappe.db.get_value ("Supplier",{"name":doc.party},["account_name","bank_account_number","ifsc", "contact_name", "mobile", "email"],as_dict=True)
        doc.account_name = bank_details.account_name
        doc.account_number = bank_details.bank_account_number
        doc.branch_code = bank_details.ifsc
        doc.contact_name = bank_details.contact_name
        doc.email = bank_details.email
        doc.mobile = bank_details.mobile
        doc.total_amount = 0
        amount = 0
        for line in doc.get("references"):
            amount = line.amount
            doc.total_amount = amount + doc.total_amount
        doc.save()
        doc.submit()



def send_payment_orders_to_razorpayx(doc, method):
    frappe.db.set_value("Payment Order",{"name":doc.name},{
            "payout_id":"",
            "payout_status":"",
            "utr":"",
            "status_message":"",
            })
    response = payout_composite_bank_account(
        mode = "NEFT",
        amount = doc.total_amount,
        purpose = "payout",
        account_name = str(doc.account_name),
        account_number = str(doc.account_number),
        account_ifsc = str(doc.branch_code),
        contact_name = str(doc.account_name),
        contact_email = str(doc.email),
        contact_mobile = str(doc.mobile),
        contact_type = "vendor",
        contact_reference = str(doc.party),
        payment_reference = str(doc.name)

        # mode = "NEFT",
        # amount = round(1, 2) * 100,
        # purpose = "payout",
        # account_name = "ZARNIK HOTEL SUPPLIES PRIVATE LIMITED",
        # account_number = 2339261005253,
        # account_ifsc = "CNRB0002339",
        # contact_name = "Rahul Jayan",
        # contact_email = "rahul@zarnik.com",
        # contact_mobile = "7736060114",
        # contact_type = "vendor",
        # contact_reference = "V00023",
        # payment_reference = "TEST"

    )
    jsonResponse = response.json()
    frappe.db.set_value("Payment Order",{"name":doc.name},{"status_message":str(response.text)})
    if response.ok:
        if str(jsonResponse["status"]) != str(doc.payout_status):
            frappe.db.set_value("Payment Order",{"name":doc.name},{
            "payout_id":str(jsonResponse["id"]),
            "payout_status":str(jsonResponse["status"]),
            "utr":str(jsonResponse["utr"]),
            "status_message":str(jsonResponse["status_details"]["description"]),
            })
        elif str(jsonResponse["status"]) == "failed":
            frappe.db.set_value("Payment Order",{"name":doc.name},{
            "payout_id":str(jsonResponse["id"]),
            "payout_status":str(jsonResponse["status"]),
            "utr":str(jsonResponse["utr"]),
            "status_message":str(jsonResponse["status_details"]["description"]),
            })
            failed_payment_order = frappe.get_doc("Payment Order", doc.name)
            failed_payment_order.cancel()

def create_payment_entries_hourly():
    for payment_orders in frappe.db.get_list("Payment Order",fields=["name", "posting_date","party", "company_bank_account", "total_amount", "utr"],filters=[["docstatus","=",1],["utr","!=","None"],["payout_status","=","processed"]]):
        if not frappe.db.exists({"doctype": "Payment Entry", "payment_order":payment_orders.name}):
            payment_entry = frappe.get_doc({
                "doctype":"Payment Entry",
                "payment_type":"Pay",
                "posting_date":payment_orders.posting_date,
                "payment_order_status":"Payment Ordered",
                "mode_of_payment":frappe.db.get_value("Mode of Payment",{"mode_of_payment":"Bank Transfer (API)"}),
                "party_type":"Supplier",
                "party":frappe.db.get_value("Supplier",{"name":payment_orders.party}),
                "bank_account": frappe.db.get_value("Bank Account",{"name":payment_orders.account_name}),
                "paid_amount":payment_orders.total_amount,
                "received_amount":payment_orders.total_amount,
                "reference_no":payment_orders.utr,
                "reference_date":payment_orders.posting_date,
                "payment_order":payment_orders.name,
                "source_exchange_rate":1,
                "target_exchange_rate":1,
                "paid_from":"RBL CA xx2044 - ZHSPL - ZHSPL"
            })
            payment_entry.save()
            payment_entry.submit()


def check_razorpayx_payment_status_hourly():
    for payment_orders in frappe.db.get_list("Payment Order",filters=[["docstatus","=",1],["payout_status","!=","processed"]], fields=["name", "payout_status", "payout_id"]):
        payout_id = payment_orders.payout_id
        payment_order = payment_orders.name
        if payout_id:
            response = fetch_transaction_by_id(payout_id)
            jsonResponse = response.json()
            if not str(jsonResponse["status"]) == str(payment_orders.payout_status):
                frappe.db.set_value("Payment Order",{"name":payment_orders.name,"payout_id":payment_orders.payout_id},{
                "payout_status":str(jsonResponse["status"]),
                "utr":str(jsonResponse["utr"]),
                "status_message":str(jsonResponse["status_details"]["description"]),
                })
            elif str(jsonResponse["status"]) == "failed":
                frappe.db.set_value("Payment Order",{"name":payment_orders.name,"payout_id":payment_orders.payout_id},{
                "payout_status":str(jsonResponse["status"]),
                "utr":str(jsonResponse["utr"]),
                "status_message":str(jsonResponse["status_details"]["description"])
                })
                failed_payment_order = frappe.get_doc("Payment Order", payment_orders.name)
                failed_payment_order.cancel()

def test():
    pass

def send_payment_notification(doc, method):
    enable_supplier_email = frappe.db.get_single_value('AP Automation Settings', 'enable_supplier_email')

    sender = frappe.db.get_single_value("AP Automation Settings","sender")
    sender = frappe.get_value("Email Account",sender,"email_id")
    attach_statement = frappe.db.get_single_value("AP Automation Settings","attach_statement")
    cc = frappe.db.get_single_value("AP Automation Settings","cc")

    email_template = frappe.db.get_single_value("AP Automation Settings","email_template")
    use_html = frappe.get_value("Email Template",email_template,"use_html")
    if use_html == 1:
        template=frappe.get_value("Email Template",email_template,"response_html")
    if use_html == 0:
        template=frappe.get_value("Email Template",email_template,"response")
    
    subject = frappe.get_value("Email Template",email_template,"subject")

    if enable_supplier_email ==1:
        from erpnext.accounts.utils import get_balance_on
        from frappe.core.doctype.communication.email import make

        if doc.payment_type == "Pay" and doc.party_type == "Supplier" and doc.payment_order:
            
            from erpnext.accounts.party import get_party_details
            party_details = get_party_details(party_type=doc.party_type, party=doc.party)
            supplier_email = party_details["contact_email"]
            cc = frappe.db.get_single_value('AP Automation Settings', 'cc')

            supplier_balance = get_balance_on(party_type="Supplier",party=doc.party)

            if supplier_email:
                try:
                    
                    recipients = [supplier_email]
                    cc = [cc]
                    bcc = []

                    import locale
                    locale.setlocale(locale.LC_MONETARY, 'en_IN')

                    data = {
                        "party_name": doc.party_name,
                        "mode_of_payment": doc.mode_of_payment,
                        "reference_no": doc.reference_no,
                        "reference_date": doc.reference_date,
                        "paid_amount": locale.currency(doc.paid_amount, grouping=True),
                        "supplier_balance": locale.currency(supplier_balance, grouping=True),
                    }

                    content = frappe.render_template(template, data)
                    subject = frappe.render_template(subject, data)
                    
                    # file = Path(__file__).with_name("email_supplier_payment_notification.html").absolute()
                    # html = file.read_text()
                    
                    # email_template = html.format(
                    #         party_name = doc.party_name,
                    #         mode_of_payment = doc.mode_of_payment,
                    #         reference_no = doc.reference_no,
                    #         reference_date = doc.reference_date,
                    #         paid_amount = locale.currency(doc.paid_amount, grouping=True),
                    #         supplier_balance = locale.currency(supplier_balance, grouping=True),
                    #         )
                    # subject = "Payment of {paid_amount} successful from Zarnik".format(
                    #         party_name = doc.party_name,
                    #         mode_of_payment = doc.mode_of_payment,
                    #         reference_no = doc.reference_no,
                    #         reference_date = doc.reference_date,
                    #         paid_amount = locale.currency(doc.paid_amount, grouping=True),
                    #         supplier_balance = locale.currency(supplier_balance, grouping=True),
                    #         )

                    attachments = []
                    if attach_statement==1:
                        from zarnik.utils import pdf_account_statement
                        attachments = pdf_account_statement(party_type=doc.party_type, party=doc.party, party_name=doc.party_name)               

                    make(
                        doctype="Payment Entry",
                        name=doc.name,
                        content=content,
                        subject=subject,
                        sender=sender,
                        reply_to=sender,
                        recipients=recipients,
                        communication_medium="Email",
                        send_email=True,
                        attachments=attachments,
                        cc=cc,
                        bcc=bcc,
                        read_receipt=True,
                    )

                except Exception as e:
                    frappe.log_error(message=e,title="Error send_payment_notification")