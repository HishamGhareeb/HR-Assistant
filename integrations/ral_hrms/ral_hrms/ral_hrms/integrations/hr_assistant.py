"""Placeholders for RAL HRMS-to-HR-Assistant sync hooks.

These functions are intentionally no-ops in the scaffold. The production
RAL HRMS app must implement queued, tenant-scoped, retryable sync calls to the
HR Assistant API without mutating RAL HRMS from AI approval paths.
"""


def enqueue_employee_sync(doc, method=None):
    pass


def enqueue_leave_sync(doc, method=None):
    pass


def enqueue_leave_revoke(doc, method=None):
    pass


def enqueue_appraisal_sync(doc, method=None):
    pass


def enqueue_salary_slip_sync(doc, method=None):
    pass
