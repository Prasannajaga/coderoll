import pytest

from app.inventory import allocate_items, is_in_stock


def test_is_in_stock_true_and_false() -> None:
    stock = {"A": 5, "B": 0}
    assert is_in_stock(stock, "A", 2) is True
    assert is_in_stock(stock, "A", 6) is False
    assert is_in_stock(stock, "B", 1) is False


def test_allocate_items_caps_to_available_stock() -> None:
    stock = {"A": 3, "B": 10}
    requested = {"A": 4, "B": 2, "C": 7}
    assert allocate_items(stock, requested) == {"A": 3, "B": 2, "C": 0}


def test_allocate_items_is_deterministic_by_sku_sorting() -> None:
    stock = {"A": 1, "B": 1}
    requested = {"B": 1, "A": 1}
    assert list(allocate_items(stock, requested).keys()) == ["A", "B"]


def test_negative_requested_qty_raises() -> None:
    with pytest.raises(ValueError):
        allocate_items({"A": 1}, {"A": -1})
