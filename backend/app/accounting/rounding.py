from decimal import Decimal, ROUND_HALF_UP

from app.accounting.policy import get_policy


def round_money(value: float | int | Decimal) -> float:
    """Round a monetary value to the policy's configured precision.

    This is the SINGLE rounding function for the entire accounting engine.
    Do not round independently in routes, services, reports or the frontend
    (Doc 09 §C).
    """
    places = get_policy().rounding_places
    d = Decimal(str(value))
    quant = Decimal("1").scaleb(-places)
    return float(d.quantize(quant, rounding=ROUND_HALF_UP))