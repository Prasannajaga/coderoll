from __future__ import annotations

from app.utils.iterables import sorted_keys


def is_in_stock(stock_by_sku: dict[str, int], sku: str, qty: int = 1) -> bool:
    if qty < 0:
        raise ValueError("qty must be >= 0")
    return stock_by_sku.get(sku, 0) >= qty


def allocate_items(stock_by_sku: dict[str, int], requested: dict[str, int]) -> dict[str, int]:
    allocated: dict[str, int] = {}
    for sku in sorted_keys(requested):
        want = requested[sku]
        if want < 0:
            raise ValueError("requested qty must be >= 0")
        available = stock_by_sku.get(sku, 0)
        take = min(want, max(available, 0))
        allocated[sku] = take
    return allocated
