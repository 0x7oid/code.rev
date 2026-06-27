"""Business calculations. Contains INTENTIONAL logic bugs for testing."""
from typing import List


def average(numbers: List[int]) -> int:
    # LOGIC + MYPY: returns float from a function annotated -> int
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)


def apply_discount(price: float, percent: float) -> float:
    # LOGIC: subtracts 'percent' as an absolute amount instead of a percentage
    return price - percent


def max_value(values):
    # LOGIC: off-by-one -> never inspects the last element
    biggest = values[0]
    for i in range(0, len(values) - 1):
        if values[i] > biggest:
            biggest = values[i]
    return biggest


def is_adult(age: int) -> bool:
    # LOGIC: should be >= 18
    return age > 18


def append_item(item, bucket=[]):
    # LOGIC: mutable default argument shared across all calls
    bucket.append(item)
    return bucket


def grade(score: int) -> str:
    # LOGIC + MYPY: no return for scores below 70 -> implicitly returns None
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
