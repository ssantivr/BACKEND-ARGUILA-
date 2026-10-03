from collections.abc import Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class _Node(Generic[T]):
    __slots__ = ("data", "previous", "next")

    def __init__(self, data: T) -> None:
        self.data = data
        self.previous: _Node[T] | None = None
        self.next: _Node[T] | None = None


class DoublyLinkedList(Generic[T]):
    """Doubly linked list with head and tail pointers. O(n) space."""

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

    def __reversed__(self) -> Iterator[T]:
        current = self._tail

        while current is not None:
            yield current.data
            current = current.previous

    def __contains__(self, value: object) -> bool:
        """O(n)."""
        return any(item == value for item in self)

    def is_empty(self) -> bool:
        return self._head is None

    def push_front(self, value: T) -> None:
        """O(1)."""
        node = _Node(value)

        if self._head is None:
            self._head = self._tail = node
        else:
            node.next = self._head
            self._head.previous = node
            self._head = node

        self._size += 1

    def push_back(self, value: T) -> None:
        """O(1)."""
        node = _Node(value)

        if self._tail is None:
            self._head = self._tail = node
        else:
            node.previous = self._tail
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

        for _ in range(index):
            assert current is not None
            current = current.next

        assert current is not None and current.previous is not None
        node = _Node(value)
        node.previous = current.previous
        node.next = current
        current.previous.next = node
        current.previous = node
        self._size += 1

    def pop_front(self) -> T:
        """O(1). Raises IndexError when the list is empty."""
        if self._head is None:
            raise IndexError("pop from empty list")

        return self._unlink(self._head)

    def pop_back(self) -> T:
        """O(1). Raises IndexError when the list is empty."""
        if self._tail is None:
            raise IndexError("pop from empty list")

        return self._unlink(self._tail)

    def remove(self, value: T) -> bool:
        """O(n). Removes the first occurrence; returns whether it was found."""
        current = self._head

        while current is not None:
            if current.data == value:
                self._unlink(current)
                return True

            current = current.next

        return False

    def clear(self) -> None:
        """O(n): links are broken explicitly so the nodes do not form cycles."""
        current = self._head

        while current is not None:
            next_node = current.next
            current.previous = current.next = None
            current = next_node

        self._head = None
        self._tail = None
        self._size = 0

    def _unlink(self, node: _Node[T]) -> T:
        """O(1). Detaches node from the list and returns its data."""
        if node.previous is not None:
            node.previous.next = node.next
        else:
            self._head = node.next

        if node.next is not None:
            node.next.previous = node.previous
        else:
            self._tail = node.previous

        self._size -= 1
        return node.data
