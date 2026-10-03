from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class _Node(Generic[T]):
    __slots__ = ("data", "next")

    def __init__(self, data: T) -> None:
        self.data = data
        self.next: _Node[T] | None = None


class SinglyLinkedList(Generic[T]):
    """Singly linked list with head and tail pointers. O(n) space."""

    def __init__(self) -> None:
        self._head: _Node[T] | None = None
        self._tail: _Node[T] | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        current = self._head

        while current is not None:
            yield current.data
            current = current.next

    def __contains__(self, value: object) -> bool:
        """O(n)."""
        return any(item == value for item in self)

    def is_empty(self) -> bool:
        return self._head is None

    def push_front(self, value: T) -> None:
        """O(1)."""
        node = _Node(value)
        node.next = self._head
        self._head = node

        if self._tail is None:
            self._tail = node

        self._size += 1

    def push_back(self, value: T) -> None:
        """O(1) thanks to the tail pointer."""
        node = _Node(value)

        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node

        self._size += 1

    def insert_at(self, index: int, value: T) -> None:
        """O(n). Valid positions: 0..len(self). Raises IndexError otherwise."""
        if index < 0 or index > self._size:
            raise IndexError("insert position out of range")

        if index == 0:
            self.push_front(value)
            return

        if index == self._size:
            self.push_back(value)
            return

        current = self._head

        for _ in range(index - 1):
            assert current is not None
            current = current.next

        assert current is not None
        node = _Node(value)
        node.next = current.next
        current.next = node
        self._size += 1

    def pop_front(self) -> T:
        """O(1). Raises IndexError when the list is empty."""
        if self._head is None:
            raise IndexError("pop from empty list")

        node = self._head
        self._head = node.next

        if self._head is None:
            self._tail = None

        self._size -= 1
        return node.data

    def remove(self, value: T) -> bool:
        """O(n). Removes the first occurrence; returns whether it was found."""
        previous: _Node[T] | None = None
        current = self._head

        while current is not None:
            if current.data == value:
                if previous is None:
                    self._head = current.next
                else:
                    previous.next = current.next

                if current is self._tail:
                    self._tail = previous

                self._size -= 1
                return True

            previous = current
            current = current.next

        return False

    def reverse(self) -> None:
        """O(n) time, O(1) extra space."""
        previous: _Node[T] | None = None
        current = self._head
        self._tail = self._head

        while current is not None:
            next_node = current.next
            current.next = previous
            previous = current
            current = next_node

        self._head = previous

    def clear(self) -> None:
        """O(1): the unreachable nodes are reclaimed by the garbage collector."""
        self._head = None
        self._tail = None
        self._size = 0
