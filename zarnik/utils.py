import frappe
from pathlib import Path
from frappe.utils import nowdate
from frappe.utils import add_to_date
from datetime import datetime
from frappe.utils import today

def pdf_account_statement(party_type, party, party_name):
    from frappe.utils.pdf import get_pdf

    from erpnext.accounts.utils import get_balance_on

    from_date = add_to_date(datetime.now(), days=-90)
    to_date = today()

    opening_balance = get_balance_on(party_type=party_type, party=party, date=add_to_date(from_date, days=-1))
    closing_balance = get_balance_on(party_type=party_type, party=party, date=to_date)

    opening_debit_balance = opening_balance if opening_balance>0 else 0
    opening_credit_balance = opening_balance if opening_balance<0 else 0
    closing_debit_balance = closing_balance if opening_balance>0 else 0
    closing_credit_balance = closing_balance if opening_balance<0 else 0

    data = {
        "party_type": party_type,
        "party": party,
        "party_name": party_name,
        "from_date": from_date,
        "to_date": to_date,
        "opening_debit_balance": opening_debit_balance,
        "opening_credit_balance": opening_credit_balance,
        "closing_debit_balance": closing_debit_balance,
        "closing_credit_balance": closing_credit_balance,
    }

    file = Path(__file__).with_name("pdf_account_statement.html").absolute()
    html = file.read_text()
    statement = frappe.render_template(html, data)

    attachments = [{
        "fname": str(party)+" "+str(party_name)+" "+str(nowdate())+".pdf",
        "fcontent": get_pdf(statement)
    }]

    return attachments