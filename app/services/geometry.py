from collections.abc import Sequence


def polygon_area(points: Sequence[tuple[float, float]]) -> float:
    total = 0.0

    for index, (x, y) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        total += x * next_y - next_x * y

    return abs(total) / 2
