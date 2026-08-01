"""Citation-backed statutory and official-operational WPS values."""

from __future__ import annotations

from glue.bahrain_payroll.citation_guard import StatutoryCitation, StatutoryValue


WPS_MAX_WORKER_RECORDS_PER_FILE = StatutoryValue(
    name="wps_max_worker_records_per_file",
    value=1000,
    unit="worker records",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="WPS User Manual",
        retrieved="2026-08-02",
        quote="Maximum **1,000 worker records per salary file**",
    ),
)

WPS_ADVANCE_SCHEDULING_WINDOW_DAYS = StatutoryValue(
    name="wps_advance_scheduling_window_days",
    value=14,
    unit="days",
    citation=StatutoryCitation(
        section="§2a-ter",
        instrument="WPS User Manual",
        retrieved="2026-08-02",
        quote="scheduled up to 14 days before the actual transfer",
    ),
)

WPS_DISCLOSURE_FIELDS_CITATION = StatutoryCitation(
    section="§2c",
    instrument="Resolution No. 68 of 2019",
    retrieved="2026-08-02",
)

