app_name = "ral_hrms"
app_title = "RAL HRMS"
app_publisher = "RAL Technologies"
app_description = (
    "RAL-owned HRMS, AI assistant, compliance, and payroll localization layer "
    "built on the RAL HRMS operations foundation."
)
app_email = "info@raltech.dev"
app_url = "https://raltech.dev"
app_license = "Proprietary RAL product layer; verify compatibility with installed RAL HRMS modules"

fixtures = [
    "Custom Field",
    "Role",
    "Workspace",
    "Print Format",
    "Property Setter",
    "Workflow",
]

doc_events = {
    "Employee": {
        "after_insert": "ral_hrms.integrations.hr_assistant.enqueue_employee_sync",
        "on_update": "ral_hrms.integrations.hr_assistant.enqueue_employee_sync",
    },
    "Leave Application": {
        "on_submit": "ral_hrms.integrations.hr_assistant.enqueue_leave_sync",
        "on_cancel": "ral_hrms.integrations.hr_assistant.enqueue_leave_revoke",
    },
    "Appraisal": {
        "on_submit": "ral_hrms.integrations.hr_assistant.enqueue_appraisal_sync",
    },
    "Salary Slip": {
        "on_submit": "ral_hrms.integrations.hr_assistant.enqueue_salary_slip_sync",
    },
}

override_whitelisted_methods = {}

