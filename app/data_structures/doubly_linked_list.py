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
        return any(item == value for item in self)

    def is_empty(self) -> bool:
        return self._head is None

    def push_front(self, value: T) -> None:
        node = _Node(value)

        if self._head is None:
            self._head = self._tail = node
        else:
            node.next = self._head
            self._head.previous = node
            self._head = node

        self._size += 1

    def push_back(self, value: T) -> None:
        node = _Node(value)

        if self._tail is None:
            self._head = self._tail = node
        else:
            node.previous = self._tail
            self._tail.next = node
            self._tail = node

        self._size += 1

    def insert_at(self, index: int, value: T) -> None:
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
        if self._head is None:
            raise IndexError("pop from empty list")

        return self._unlink(self._head)

    def pop_back(self) -> T:
        if self._tail is None:
            raise IndexError("pop from empty list")

        return self._unlink(self._tail)

    def remove(self, value: T) -> bool:
        current = self._head

        while current is not None:
            if current.data == value:
                self._unlink(current)
                return True

            current = current.next

        return False

    def clear(self) -> None:
        current = self._head

        while current is not None:
            next_node = current.next
            current.previous = current.next = None
            current = next_node

        self._head = None
        self._tail = None
        self._size = 0

    def _unlink(self, node: _Node[T]) -> T:
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
