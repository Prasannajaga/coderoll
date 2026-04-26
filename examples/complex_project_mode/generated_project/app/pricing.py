from __future__ import annotations

from dataclasses import dataclass


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
    return round(item.qty * item.unit_price, 2)


def calculate_order_total(
    items: list[LineItem],
    tax_rate: float,
    shipping: float,
    discount: float = 0.0,
) -> float:
    if tax_rate < 0:
        raise ValueError("tax_rate must be >= 0")
    if shipping < 0:
        raise ValueError("shipping must be >= 0")

    subtotal = round(sum(line_total(item) for item in items), 2)
    taxed = round(subtotal * (1.0 + tax_rate), 2)
    total = round(taxed + shipping - discount, 2)
    return max(total, 0.0)


def build_receipt(
    items: list[LineItem],
    tax_rate: float,
    shipping: float,
    discount: float = 0.0,
) -> dict[str, float]:
    subtotal = round(sum(line_total(item) for item in items), 2)
    tax = round(subtotal * tax_rate, 2)
    total = calculate_order_total(
        items=items,
        tax_rate=tax_rate,
        shipping=shipping,
        discount=discount,
    )
    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": round(shipping, 2),
        "discount": round(discount, 2),
        "total": total,
    }
