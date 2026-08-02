"""Bahrain deterministic payroll rule-pack namespace.

Rules in this package must never embed statutory numbers from memory.
Put statutory rates, thresholds, caps, deadlines, and day/month counts in
``statutory_values.py`` as ``StatutoryValue`` entries with citations back to
``docs/BAHRAIN_PAYROLL_SOURCES.md``. The citation guard test enforces this in
CI before payroll logic can merge.
"""

