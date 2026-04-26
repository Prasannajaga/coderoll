from __future__ import annotations

from app.domain.models import AllocationPlan, PlannedOrder
from app.inventory import allocate_items
from app.pricing import LineItem, build_receipt
from app.rules.discounts import bulk_units_discount, loyalty_discount


def plan_order(
    *,
    stock_by_sku: dict[str, int],
    requested: dict[str, int],
    unit_prices: dict[str, float],
    tax_rate: float,
    shipping: float,
    is_loyal_customer: bool = False,
) -> PlannedOrder:
    allocated = allocate_items(stock_by_sku, requested)
    missing = {
        sku: max(requested.get(sku, 0) - allocated.get(sku, 0), 0)
        for sku in sorted(requested)
    }

    line_items = [
        LineItem(sku=sku, qty=qty, unit_price=unit_prices.get(sku, 0.0))
        for sku, qty in allocated.items()
        if qty > 0
    ]

    subtotal = sum(item.qty * item.unit_price for item in line_items)
    total_units = sum(item.qty for item in line_items)
    discount = loyalty_discount(subtotal, is_loyal_customer=is_loyal_customer) + bulk_units_discount(
        total_units
    )

    receipt = build_receipt(
        items=line_items,
        tax_rate=tax_rate,
        shipping=shipping,
        discount=discount,
    )

    return PlannedOrder(
        allocation=AllocationPlan(allocated=allocated, missing=missing),
        receipt=receipt,
    )
