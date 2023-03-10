from . import __version__ as app_version

app_name = "zarnik"
app_title = "Zarnik"
app_publisher = "Zarnik Hotel Supplies Private Limited"
app_description = "ERPNext customizations for Zarnik Hotel Supplies Private Limited"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "azhar@zarnik.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/zarnik/css/zarnik.css"
# app_include_js = "/assets/zarnik/js/zarnik.js"

# include js, css files in header of web template
# web_include_css = "/assets/zarnik/css/zarnik.css"
# web_include_js = "/assets/zarnik/js/zarnik.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "zarnik/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "zarnik.install.before_install"
# after_install = "zarnik.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "zarnik.uninstall.before_uninstall"
# after_uninstall = "zarnik.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "zarnik.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Order" : {"on_submit": "zarnik.ap_automation.payments.schedule_payment_requests"},
	"Purchase Invoice" : {"on_submit": "zarnik.ap_automation.payments.schedule_payment_requests"},
	"Payment Order" : {"on_submit": "zarnik.ap_automation.payments.send_payment_orders_to_razorpayx"},
	"Payment Entry" : {"on_submit": "zarnik.ap_automation.payments.send_payment_notification"},
	"Sales Order" : {"on_submit": "zarnik.validations.sales_order_before_submit"}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"0 6 * * 1": ["zarnik.ap_automation.payments.create_payment_orders_weekly"],
		"5 * * * *": ["zarnik.ap_automation.payments.test"],
		"1/10 * * * *": [
			"zarnik.ap_automation.payments.check_razorpayx_payment_status_hourly",
			"zarnik.ap_automation.payments.create_payment_entries_hourly",
		],
		"0 19 * * *": ["zarnik.ar_automation.tasks.send_invoice_daily"]
	},
#	"all": [
#		"zarnik.tasks.all"
#	],
	"daily": [
		"zarnik.procurement_automation.tasks.create_purchase_orders",
	],
	"hourly": [
		"zarnik.ap_automation.payments.create_payment_orders_hourly",
	],
	"weekly": [
		"zarnik.procurement_automation.tasks.set_reorder_values",
		"zarnik.procurement_automation.tasks.disable_inactive_items",
	]
#	"monthly": [
#		"zarnik.tasks.monthly"
#	]
}

# Testing
# -------

# before_tests = "zarnik.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "zarnik.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "zarnik.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"zarnik.auth.validate"
# ]

