from __future__ import annotations


def to_money(value: float) -> float:
    return round(value, 2)


def clamp_non_negative(value: float) -> float:
    return value if value > 0 else 0.0


def apply_tax(subtotal: float, tax_rate: float) -> float:
    if tax_rate < 0:
        raise ValueError("tax_rate must be >= 0")
    return to_money(subtotal * tax_rate)
