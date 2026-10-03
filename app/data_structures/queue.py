from typing import Generic, TypeVar

T = TypeVar("T")


class Queue(Generic[T]):
    """Fixed-capacity FIFO queue backed by a circular array.

    Slots freed by dequeue are reused, so the queue only reports full when it
    really holds `capacity` elements. O(capacity) space.
    """

    def __init__(self, capacity: int = 100) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self._items: list[T | None] = [None] * capacity
        self._front = 0
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

    def enqueue(self, value: T) -> None:
        """O(1). Raises OverflowError when the queue is full."""
        if self.is_full():
            raise OverflowError("queue is full")

        self._items[(self._front + self._size) % len(self._items)] = value
        self._size += 1

    def dequeue(self) -> T:
        """O(1). Raises IndexError when the queue is empty."""
        if self.is_empty():
            raise IndexError("dequeue from empty queue")

        value = self._items[self._front]
        self._items[self._front] = None
        self._front = (self._front + 1) % len(self._items)
        self._size -= 1
        return value  # type: ignore[return-value]

    def peek(self) -> T:
        """O(1). Raises IndexError when the queue is empty."""
        if self.is_empty():
            raise IndexError("peek from empty queue")

        return self._items[self._front]  # type: ignore[return-value]

    def clear(self) -> None:
        """O(capacity)."""
        self._items = [None] * len(self._items)
        self._front = 0
        self._size = 0
