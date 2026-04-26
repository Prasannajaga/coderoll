from __future__ import annotations


from .taxing import to_money


def loyalty_discount(subtotal: float, *, is_loyal_customer: bool) -> float:
    if not is_loyal_customer:
        return 0.0
    return to_money(min(subtotal * 0.05, 25.0))


def bulk_units_discount(total_units: int) -> float:
    if total_units >= 20:
        return 10.0
    if total_units >= 10:
        return 4.0
    return 0.0
