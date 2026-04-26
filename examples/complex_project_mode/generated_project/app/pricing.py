from __future__ import annotations

from dataclasses import dataclass

from app.rules.taxing import apply_tax, clamp_non_negative, to_money


@dataclass(frozen=True)
class LineItem:
    sku: str
    qty: int
    unit_price: float


def line_total(item: LineItem) -> float:
    if item.qty < 0:
        raise ValueError("qty must be >= 0")
    if item.unit_price < 0:
        raise ValueError("unit_price must be >= 0")
    return to_money(item.qty * item.unit_price)


def calculate_order_total(
    items: list[LineItem],
    tax_rate: float,
    shipping: float,
    discount: float = 0.0,
) -> float:
    if shipping < 0:
        raise ValueError("shipping must be >= 0")

    subtotal = to_money(sum(line_total(item) for item in items))
    tax = apply_tax(subtotal, tax_rate)
    total = to_money(subtotal + tax + shipping - discount)
    return clamp_non_negative(total)


def build_receipt(
    items: list[LineItem],
    tax_rate: float,
    shipping: float,
    discount: float = 0.0,
) -> dict[str, float]:
    subtotal = to_money(sum(line_total(item) for item in items))
    tax = apply_tax(subtotal, tax_rate)
    total = calculate_order_total(
        items=items,
        tax_rate=tax_rate,
        shipping=shipping,
        discount=discount,
    )
    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": to_money(shipping),
        "discount": to_money(discount),
        "total": total,
    }
