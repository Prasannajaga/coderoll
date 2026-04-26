from app.services.order_planner import plan_order


def test_plan_order_applies_loyalty_and_bulk_discounts() -> None:
    planned = plan_order(
        stock_by_sku={"A": 20, "B": 5},
        requested={"A": 12, "B": 3, "C": 2},
        unit_prices={"A": 10.0, "B": 5.0, "C": 99.0},
        tax_rate=0.10,
        shipping=4.0,
        is_loyal_customer=True,
    )

    assert planned.allocation.allocated == {"A": 12, "B": 3, "C": 0}
    assert planned.allocation.missing == {"A": 0, "B": 0, "C": 2}
    assert planned.receipt == {
        "subtotal": 135.0,
        "tax": 13.5,
        "shipping": 4.0,
        "discount": 10.75,
        "total": 141.75,
    }


def test_plan_order_without_loyalty_has_no_percentage_discount() -> None:
    planned = plan_order(
        stock_by_sku={"A": 3},
        requested={"A": 2},
        unit_prices={"A": 8.0},
        tax_rate=0.0,
        shipping=0.0,
        is_loyal_customer=False,
    )

    assert planned.receipt["discount"] == 0.0
    assert planned.receipt["total"] == 16.0
