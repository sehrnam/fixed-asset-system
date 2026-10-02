"""
Centralized accounting-policy configuration.

Every rule tagged DEMO is a project/demo implementation decision, NOT a claim
about any real bank's accounting policy (Document 09, Doc 08 freeze rule).

This is the ONLY place accounting rules may live. Routes, UI components and
report code must call into the engine, never re-implement these rules.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AccountingPolicy:
    # Doc 09 #1 — Depreciation commencement
    commencement_rule: str = "acquisition_date"

    # Doc 09 #2 — Partial-year convention
    partial_year_rule: str = "monthly_proration_acquisition_month_full"

    # Doc 09 #3 — Rounding
    rounding_places: int = 2
    rounding_stage: str = "after_method_before_persistence"

    # Doc 09 #4 — Reducing-balance residual floor
    rb_residual_floor: bool = True
    allow_negative_depreciation: bool = False

    # Doc 09 #5 — Disposal gain/loss
    disposal_gain_loss_rule: str = "proceeds_minus_nbv_at_disposal"

    # Doc 09 #6 — Journal mode
    journal_mode: str = "prepare_export_only"

    # Provenance marker for audit/UI
    source: str = "DEMO"


DEMO_POLICY = AccountingPolicy()


def get_policy() -> AccountingPolicy:
    """Return the currently-active accounting policy.

    In a future institutional deployment this function would read from a
    persisted policy table; for the project/demo it returns the frozen DEMO
    policy (Doc 09 release rule).
    """
    return DEMO_POLICY