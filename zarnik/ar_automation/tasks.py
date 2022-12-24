import frappe
from frappe.utils import now

def send_invoice_daily():
    recipients = [
    'azhar.umar@gmail.com'
    ]

    cc = []

    frappe.sendmail(
        recipients=recipients,
        cc=cc
        subject="Testime Email ",
        message="Hello ",
        expose_recipients=`header`,
        as_markdown=False, 
        template=None, 
        args=None, 
    )


# @frappe.whitelist()
# def getData():
# 	try:
# 		request_doc=frappe.get_all("Purchase Order",filters={"schedule_date":add_days(today(),1)},fields=["name"])
# 		return request_doc
# 		if request_doc:
# 			for doc in request_doc:
# 				po_doc=frappe.get_doc("Purchase Order",doc.name)
# 				supplier_email=getSupplierEmail(po_doc.supplier)
#                             #write email send logic#
				

# 	except Exception as e:
# 		return generateResponse("F",error=e)

# @frappe.whitelist()
# def getSupplierEmail(supplier):
# 	supplier_doc=frappe.get_all("Contact",filters=[["Dynamic Link","link_doctype","=","Supplier"],["Dynamic Link","link_name","=",supplier]],fields=["email_id"])
# 	return supplier_doc[0].email_id


# def sendmail(
# 	recipients=None,
# 	sender="",
# 	subject="No Subject",
# 	message="No Message",
# 	as_markdown=False,
# 	delayed=True,
# 	reference_doctype=None,
# 	reference_name=None,
# 	unsubscribe_method=None,
# 	unsubscribe_params=None,
# 	unsubscribe_message=None,
# 	add_unsubscribe_link=1,
# 	attachments=None,
# 	content=None,
# 	doctype=None,
# 	name=None,
# 	reply_to=None,
# 	queue_separately=False,
# 	cc=None,
# 	bcc=None,
# 	message_id=None,
# 	in_reply_to=None,
# 	send_after=None,
# 	expose_recipients=None,
# 	send_priority=1,
# 	communication=None,
# 	retry=1,
# 	now=None,
# 	read_receipt=None,
# 	is_notification=False,
# 	inline_images=None,
# 	template=None,
# 	args=None,
# 	header=None,
# 	print_letterhead=False,
# 	with_container=False,
# ):
# 	"""Send email using user's default **Email Account** or global default **Email Account**.
# 	:param recipients: List of recipients.
# 	:param sender: Email sender. Default is current user or default outgoing account.
# 	:param subject: Email Subject.
# 	:param message: (or `content`) Email Content.
# 	:param as_markdown: Convert content markdown to HTML.
# 	:param delayed: Send via scheduled email sender **Email Queue**. Don't send immediately. Default is true
# 	:param send_priority: Priority for Email Queue, default 1.
# 	:param reference_doctype: (or `doctype`) Append as communication to this DocType.
# 	:param reference_name: (or `name`) Append as communication to this document name.
# 	:param unsubscribe_method: Unsubscribe url with options email, doctype, name. e.g. `/api/method/unsubscribe`
# 	:param unsubscribe_params: Unsubscribe paramaters to be loaded on the unsubscribe_method [optional] (dict).
# 	:param attachments: List of attachments.
# 	:param reply_to: Reply-To Email Address.
# 	:param message_id: Used for threading. If a reply is received to this email, Message-Id is sent back as In-Reply-To in received email.
# 	:param in_reply_to: Used to send the Message-Id of a received email back as In-Reply-To.
# 	:param send_after: Send after the given datetime.
# 	:param expose_recipients: Display all recipients in the footer message - "This email was sent to"
# 	:param communication: Communication link to be set in Email Queue record
# 	:param inline_images: List of inline images as {"filename", "filecontent"}. All src properties will be replaced with random Content-Id
# 	:param template: Name of html template from templates/emails folder
# 	:param args: Arguments for rendering the template
# 	:param header: Append header in email
# 	:param with_container: Wraps email inside a styled container