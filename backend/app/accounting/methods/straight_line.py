from app.models.asset import Asset


def annual_depreciation(asset: Asset) -> float:
    """Annual straight-line depreciation.

    Source formula (Doc 04 §2):  (Cost - Residual Value) / Useful Life
    """
    return (asset.cost - asset.residual_value) / asset.useful_life_years


def period_depreciation(asset: Asset, months_this_period: int) -> float:
    """Depreciation for a period of `months_this_period` months.

    Under the frozen demo policy, monthly pro-rating is applied to the annual
    figure. Acquisition month counts as a full month, so `months_this_period`
    is always an integer.
    """
    annual = annual_depreciation(asset)
    monthly = annual / 12.0
    return monthly * months_this_period