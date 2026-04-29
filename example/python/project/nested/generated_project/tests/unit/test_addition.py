from services.calculator.core.addition import add_many, add_one


def test_add_one() -> None:
    assert add_one(9) == 10


def test_add_many() -> None:
    assert add_many(3, [1, 2, 3]) == 9
