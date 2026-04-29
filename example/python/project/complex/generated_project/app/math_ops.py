def add(value: int, step: int = 1) -> int:
    return value + step


def add_many(start: int, deltas: list[int]) -> int:
    total = start
    for delta in deltas:
        total = add(total, delta)
    return total
