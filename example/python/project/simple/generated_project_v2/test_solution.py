from solution import add_one


def test_add_one_values() -> None:
    assert add_one(0) == 1
    assert add_one(10) == 11
