def add_one(value: int) -> int:
    return value + 1


def add_many(start: int, increments: list[int]) -> int:
    total = start
    for inc in increments:
        total += inc
    return total
