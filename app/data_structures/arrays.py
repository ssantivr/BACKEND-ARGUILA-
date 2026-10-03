from collections.abc import Iterator, Sequence
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def linear_search(values: Sequence[T], target: T) -> int:
    """O(n). Returns the index of target or -1 if it is not present."""
    for index, value in enumerate(values):
        if value == target:
            return index

    return -1


def binary_search(values: Sequence[Any], target: Any) -> int:
    """O(log n). Requires values sorted in ascending order. Returns -1 if absent."""
    low = 0
    high = len(values) - 1

    while low <= high:
        middle = (low + high) // 2

        if values[middle] == target:
            return middle

        if values[middle] < target:
            low = middle + 1
        else:
            high = middle - 1

    return -1


class DynamicArray(Generic[T]):
    """Array that doubles its capacity when full. Amortized O(1) append."""

    def __init__(self, capacity: int = 4) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._items: list[T | None] = [None] * capacity
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        for index in range(self._size):
            yield self._items[index]  # type: ignore[misc]

    def __getitem__(self, index: int) -> T:
        """O(1)."""
        self._check_index(index)
        return self._items[index]  # type: ignore[return-value]

    def __setitem__(self, index: int, value: T) -> None:
        """O(1)."""
        self._check_index(index)
        self._items[index] = value

    @property
    def capacity(self) -> int:
        return len(self._items)

    def append(self, value: T) -> None:
        """Amortized O(1)."""
        self.insert_at(self._size, value)

    def insert_at(self, index: int, value: T) -> None:
        """O(n). Shifts elements right. Valid positions: 0..len(self)."""
        if index < 0 or index > self._size:
            raise IndexError("insert position out of range")

        if self._size == len(self._items):
            self._resize(2 * len(self._items))

        for position in range(self._size, index, -1):
            self._items[position] = self._items[position - 1]

        self._items[index] = value
        self._size += 1

    def remove_at(self, index: int) -> T:
        """O(n). Shifts elements left and returns the removed value."""
        self._check_index(index)
        removed = self._items[index]

        for position in range(index, self._size - 1):
            self._items[position] = self._items[position + 1]

        self._size -= 1
        self._items[self._size] = None
        return removed  # type: ignore[return-value]

    def _resize(self, capacity: int) -> None:
        """O(n). Allocates a larger block and copies the elements."""
        resized: list[T | None] = [None] * capacity

        for index in range(self._size):
            resized[index] = self._items[index]

        self._items = resized

    def _check_index(self, index: int) -> None:
        if index < 0 or index >= self._size:
            raise IndexError("index out of range")
