import pytest

from app.pricing import LineItem, build_receipt, calculate_order_total, line_total


def test_line_total_rounding() -> None:
    item = LineItem(sku="A", qty=3, unit_price=19.995)
    assert line_total(item) == 59.98


def test_calculate_order_total_with_tax_discount_and_shipping() -> None:
    items = [
        LineItem(sku="A", qty=2, unit_price=20.0),
        LineItem(sku="B", qty=1, unit_price=10.0),
    ]
    total = calculate_order_total(items, tax_rate=0.10, shipping=5.0, discount=3.0)
    assert total == 57.0


def test_order_total_never_negative() -> None:
    items = [LineItem(sku="A", qty=1, unit_price=5.0)]
    total = calculate_order_total(items, tax_rate=0.0, shipping=0.0, discount=99.0)
    assert total == 0.0


def test_receipt_breakdown_values() -> None:
    items = [LineItem(sku="A", qty=1, unit_price=50.0)]
    receipt = build_receipt(items, tax_rate=0.08, shipping=4.5, discount=1.0)
    assert receipt == {
        "subtotal": 50.0,
        "tax": 4.0,
        "shipping": 4.5,
        "discount": 1.0,
        "total": 57.5,
    }


@pytest.mark.parametrize(
    "tax_rate,shipping",
    [(-0.1, 0.0), (0.1, -1.0)],
)
def test_invalid_totals_raise(tax_rate: float, shipping: float) -> None:
    with pytest.raises(ValueError):
        calculate_order_total([], tax_rate=tax_rate, shipping=shipping)
