"""
Centralized accounting-policy configuration.

v3.0 — Supersedes v2.2. Reflects the 2026-10-09 authoritative revision:
  - Straight-line only (reducing-balance removed from active workflow)
  - Monthly periods, calculation date = last calendar day of the month
  - First-month proration excluding the acquisition date itself
  - Cap cumulative depreciation at (cost - residual)
  - Automatic monthly runs; PDF generated per run

Every rule here is a project/demo implementation decision, NOT a claim about
any real bank's accounting policy. All rules live in this one file; routes,
UI, and report code call into the engine and never re-implement these rules.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AccountingPolicy:
    # --- Depreciation method (v3.0: straight-line only) ---
    method: str = "straight_line"

    # --- Commencement ---
    commencement_rule: str = "acquisition_date"

    # --- Period model (v3.0: monthly) ---
    period_granularity: str = "monthly"
    period_end_rule: str = "last_calendar_day_of_month"

    # --- First-month proration (v3.0) ---
    # Exclude the acquisition date itself. Eligible days = days_in_month - day.
    # First-month dep = (monthly_amount) * (eligible_days / days_in_month).
    first_month_rule: str = "days_prorated_excluding_acquisition_date"

    # --- Subsequent months (v3.0) ---
    subsequent_month_rule: str = "full_monthly_amount"

    # --- Rounding ---
    rounding_places: int = 2
    rounding_stage: str = "after_method_before_persistence"

    # --- Caps and floors (v3.0) ---
    # Never allow cumulative depreciation to exceed (cost - residual).
    cumulative_cap: str = "cost_minus_residual"
    # Closing NBV never falls below residual.
    residual_floor: bool = True
    allow_negative_depreciation: bool = False

    # --- End of useful life (v3.0: continue until cap, then cap final month) ---
    useful_life_end_rule: str = "continue_until_cap_then_cap_final_month"

    # --- Automatic monthly runs (v3.0) ---
    auto_depreciation: bool = True
    auto_run_trigger: str = "startup_catchup"  # catch-up on each app start
    auto_generate_pdf: bool = True

    # --- Disposal gain/loss ---
    disposal_gain_loss_rule: str = "proceeds_minus_nbv_at_disposal"

    # --- Journal mode ---
    journal_mode: str = "prepare_export_only"

    # --- Provenance marker ---
    source: str = "DEMO_v3.0"
    effective_from: str = "2026-10-09"


DEMO_POLICY = AccountingPolicy()


def get_policy() -> AccountingPolicy:
    """Return the currently-active accounting policy.

    In a future institutional deployment this function would read from a
    persisted policy table; for the project/demo it returns the frozen DEMO
    policy.
    """
    return DEMO_POLICY