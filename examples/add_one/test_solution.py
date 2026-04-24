from solution import solution


def test_add_one():
    assert solution(1) == 2
    assert solution(10) == 11
    assert solution(-1) == 0
