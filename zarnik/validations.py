import frappe

def sales_order_before_submit(doc, method):
    from erpnext.accounts.party import get_party_details
    party_details = get_party_details(party_type="Customer", party=doc.customer)
    primary_mobile, primary_email = frappe.db.get_value("Customer",doc.customer, ["mobile_no", "email_id"])
    details_not_found = ""
    if not party_details.contact_email:
        details_not_found = "<li>Primary Email in Contact document</li>"
    if not party_details.contact_mobile:
        details_not_found = details_not_found + "<li>Primary Mobile in Contact document.</li>"
    if not (primary_mobile or primary_email):
        details_not_found = details_not_found + "<li>Customer Primary Contact in Customer document.</li>"
    if details_not_found:
        frappe.throw("Following details were not found for "+doc.customer_name+":<br><br><ul>"+details_not_found+"</ul>"+"The above details are mandatory for automated communications to customer.")

