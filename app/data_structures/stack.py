from typing import Generic, TypeVar

T = TypeVar("T")


class Stack(Generic[T]):
    """Fixed-capacity LIFO stack backed by an array. O(capacity) space."""

    def __init__(self, capacity: int = 100) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._items: list[T | None] = [None] * capacity
        self._size = 0

    def __len__(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return self._size == 0

    def is_full(self) -> bool:
        return self._size == len(self._items)

    def push(self, value: T) -> None:
        """O(1). Raises OverflowError when the stack is full."""
        if self.is_full():
            raise OverflowError("stack is full")

        self._items[self._size] = value
        self._size += 1

    def pop(self) -> T:
        """O(1). Raises IndexError when the stack is empty."""
        if self.is_empty():
            raise IndexError("pop from empty stack")

        self._size -= 1
        value = self._items[self._size]
        self._items[self._size] = None
        return value  # type: ignore[return-value]

    def peek(self) -> T:
        """O(1). Raises IndexError when the stack is empty."""
        if self.is_empty():
            raise IndexError("peek from empty stack")

        return self._items[self._size - 1]  # type: ignore[return-value]

    def clear(self) -> None:
        """O(capacity)."""
        self._items = [None] * len(self._items)
        self._size = 0
