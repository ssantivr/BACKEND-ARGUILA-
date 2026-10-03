from typing import Generic, TypeVar

T = TypeVar("T")


class Queue(Generic[T]):
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
        if self.is_full():
            raise OverflowError("queue is full")

        self._items[(self._front + self._size) % len(self._items)] = value
        self._size += 1

    def dequeue(self) -> T:
        if self.is_empty():
            raise IndexError("dequeue from empty queue")

        value = self._items[self._front]
        self._items[self._front] = None
        self._front = (self._front + 1) % len(self._items)
        self._size -= 1
        return value

    def peek(self) -> T:
        if self.is_empty():
            raise IndexError("peek from empty queue")

        return self._items[self._front]

    def clear(self) -> None:
        self._items = [None] * len(self._items)
        self._front = 0
        self._size = 0
