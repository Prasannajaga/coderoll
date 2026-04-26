from app.math_utils import add_one


def test_add_one():
    assert add_one(1) == 2
    assert add_one(10) == 11
    assert add_one(-1) == 0
