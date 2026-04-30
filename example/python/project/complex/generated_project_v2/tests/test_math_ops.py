from app.math_ops import add, add_many


def test_add_default_step() -> None:
    assert add(5) == 6


def test_add_many_sequence() -> None:
    assert add_many(1, [2, 3, 4]) == 10
