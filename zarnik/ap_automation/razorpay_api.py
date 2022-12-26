import frappe
import time
import asyncio

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

enable_razorpay = frappe.db.get_single_value('AP Automation Settings', 'enable_razorpay')
rzpay_key_id = frappe.db.get_single_value('AP Automation Settings', 'rzpay_key_id')
rzpay_key_secret = frappe.db.get_single_value('AP Automation Settings', 'rzpay_key_secret')
from_account = frappe.db.get_single_value('AP Automation Settings', 'rzpay_account_number')

auth = HTTPBasicAuth(rzpay_key_id, rzpay_key_secret)

def payout_composite_bank_account(**payout_info):

    ## Documentation : https://razorpay.com/docs/api/x/payout-composite ##

    # mode = "NEFT"
    # amount =  round(1, 2) * 100
    # purpose = "payout"
    # account_name = "ZARNIK HOTEL SUPPLIES PRIVATE LIMITED"
    # account_number = "2339261005253"
    # account_ifsc = "CNRB0002339"
    # contact_name = "Rahul Jayan"
    # contact_email = "rahul@zarnik.com"
    # contact_mobile = "7736060114"
    # contact_type = "vendor"
    # contact_reference = "V00023"
    # payment_reference = "TEST"
    # narration = "TEST"

    mode = str(payout_info["mode"])
    amount = int(float(payout_info["amount"]) * 100)
    purpose = str(payout_info["purpose"]) 
    account_name = str(payout_info["account_name"]) 
    account_number = str(payout_info["account_number"]) 
    account_ifsc = str(payout_info["account_ifsc"] )
    contact_name = str(payout_info["contact_name"]) 
    # contact_email = str(payout_info["contact_email"])
    # contact_mobile = str(payout_info["contact_mobile"]) 
    contact_type = str(payout_info["contact_type"])
    contact_reference = str(payout_info["contact_reference"]).replace("-"," ")
    payment_reference = str(payout_info["payment_reference"]) .replace("-"," ")
    narration = str("ZARNIK " + str(payout_info["contact_reference"]).replace("-"," ") + " " + str(payout_info["payment_reference"]).replace("-"," "))

    url = "https://api.razorpay.com/v1/payouts"
    headers = {"X-Payout-Idempotency" : ""}

    payload = {
            "mode": mode,
            "amount": amount,
            "purpose": purpose,                         
            "currency": "INR",
            "narration": narration,
            "fund_account": {
                "account_type": "bank_account",
                "bank_account": {
                    "name": account_name,
                    "ifsc": account_ifsc,
                    "account_number": account_number
                },
                "contact": {
                    "name": contact_name,
                    # "email": contact_email,
                    # "contact": contact_mobile,
                    "type": contact_type,
                    "reference_id": contact_reference
                }
            },
            "reference_id": payment_reference,
            "account_number": str(from_account),
            "queue_if_low_balance": bool(1)
            }

    if enable_razorpay == 1:
        try:
            response = requests.request("POST", url, auth=auth, headers=headers, json=payload)
            print(response.text)
            return response

        except HTTPError as http_err:
            frappe.log_error(message=f'{http_err}',title="RazorpayX HTTP Error")
            print(response.text)
            return response

        except Exception as err:
            frappe.log_error(message=f'{err}',title="Razorpayx Payout Composit API Error")
            print(response.text)
            return response

def fetch_transaction_by_id(payout_id="xyz"):

    ## Documentation : https://razorpay.com/docs/api/x/transactions#fetch-transaction-by-id ##

    if enable_razorpay == 1:
        if payout_id:
            try:
                url = "https://api.razorpay.com/v1/payouts/"+payout_id
                response = requests.request("GET", url, auth=auth)
                print(response.json())
                return response

            except HTTPError as http_err:
                frappe.log_error(message=f'{http_err}',title=f'RazorpayX HTTP Error: {payment_order}')
                print(response.json())
                return response

            except Exception as err:
                frappe.log_error(message=f'{err}',title=f'RazorpayX: {payment_order}')
                print(response.json())
                return response