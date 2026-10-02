from app.models.asset import Asset


def period_depreciation_before_floor(
    asset: Asset,
    opening_nbv: float,
    months_this_period: int,
) -> float:
    """Reducing-balance depreciation, before applying the residual floor.

    Source formula (Doc 04 §3):  Opening NBV x Rate%
    Then pro-rated for the number of chargeable months in the period.
    """
    if asset.rate is None:
        return 0.0
    annual = opening_nbv * (asset.rate / 100.0)
    monthly = annual / 12.0
    return monthly * months_this_period


def apply_residual_floor(
    depreciation: float,
    opening_nbv: float,
    residual_value: float,
) -> float:
    """Cap depreciation so closing NBV never falls below the residual value.

    Frozen demo policy (Doc 09 #4):
      Allowed depreciation = min(calculated, opening - residual)
      Never negative.
    """
    max_allowed = opening_nbv - residual_value
    if max_allowed < 0:
        return 0.0
    return min(depreciation, max_allowed)