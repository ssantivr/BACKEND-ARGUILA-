import pytest

from app.data_structures import (
    DoublyLinkedList,
    DynamicArray,
    Queue,
    SinglyLinkedList,
    Stack,
    binary_search,
    linear_search,
)


def test_stack_is_lifo():
    stack: Stack[int] = Stack()

    for value in (10, 20, 30):
        stack.push(value)

    assert len(stack) == 3
    assert stack.peek() == 30
    assert [stack.pop(), stack.pop(), stack.pop()] == [30, 20, 10]
    assert stack.is_empty()


def test_stack_underflow_and_overflow():
    stack: Stack[int] = Stack(capacity=2)

    with pytest.raises(IndexError):
        stack.pop()
    with pytest.raises(IndexError):
        stack.peek()

    stack.push(1)
    stack.push(2)

    assert stack.is_full()
    with pytest.raises(OverflowError):
        stack.push(3)
    assert stack.peek() == 2


def test_stack_accepts_falsy_values_and_clear():
    stack: Stack[int | None] = Stack()
    stack.push(0)
    stack.push(None)

    assert stack.pop() is None
    assert stack.pop() == 0

    stack.push(5)
    stack.clear()
    assert stack.is_empty()


def test_queue_is_fifo():
    queue: Queue[int] = Queue()

    for value in (10, 20, 30):
        queue.enqueue(value)

    assert len(queue) == 3
    assert queue.peek() == 10
    assert [queue.dequeue(), queue.dequeue(), queue.dequeue()] == [10, 20, 30]
    assert queue.is_empty()


def test_queue_underflow_and_overflow():
    queue: Queue[int] = Queue(capacity=2)

    with pytest.raises(IndexError):
        queue.dequeue()
    with pytest.raises(IndexError):
        queue.peek()

    queue.enqueue(1)
    queue.enqueue(2)

    assert queue.is_full()
    with pytest.raises(OverflowError):
        queue.enqueue(3)


def test_queue_reuses_freed_slots():
    queue: Queue[int] = Queue(capacity=3)
    dequeued = []

    for value in range(10):
        queue.enqueue(value)
        queue.enqueue(value + 100)
        dequeued.append(queue.dequeue())
        dequeued.append(queue.dequeue())

    assert queue.is_empty()
    assert dequeued[:4] == [0, 100, 1, 101]
    assert dequeued[-1] == 109


def test_queue_keeps_order_across_wrap_around():
    queue: Queue[int] = Queue(capacity=3)
    queue.enqueue(1)
    queue.enqueue(2)
    queue.dequeue()
    queue.enqueue(3)
    queue.enqueue(4)

    assert queue.is_full()
    assert [queue.dequeue(), queue.dequeue(), queue.dequeue()] == [2, 3, 4]


@pytest.mark.parametrize("structure", [Stack, Queue, DynamicArray])
def test_capacity_must_be_positive(structure):
    with pytest.raises(ValueError):
        structure(capacity=0)


@pytest.mark.parametrize("list_type", [SinglyLinkedList, DoublyLinkedList])
def test_linked_list_insertions(list_type):
    items = list_type()
    assert items.is_empty()

    items.push_back(10)
    items.push_back(20)
    items.push_front(5)
    items.insert_at(1, 7)
    items.insert_at(0, 1)
    items.insert_at(len(items), 99)

    assert list(items) == [1, 5, 7, 10, 20, 99]
    assert len(items) == 6
    assert 7 in items
    assert 8 not in items

    with pytest.raises(IndexError):
        items.insert_at(7, 0)
    with pytest.raises(IndexError):
        items.insert_at(-1, 0)


@pytest.mark.parametrize("list_type", [SinglyLinkedList, DoublyLinkedList])
def test_linked_list_remove_head_middle_tail(list_type):
    items = list_type()

    for value in (1, 2, 3, 4):
        items.push_back(value)

    assert items.remove(1)
    assert items.remove(3)
    assert items.remove(4)
    assert not items.remove(42)
    assert list(items) == [2]

    items.push_back(5)
    assert list(items) == [2, 5]

    assert items.remove(2)
    assert items.remove(5)
    assert items.is_empty()

    items.push_back(6)
    assert list(items) == [6]


@pytest.mark.parametrize("list_type", [SinglyLinkedList, DoublyLinkedList])
def test_linked_list_pop_front_and_clear(list_type):
    items = list_type()

    with pytest.raises(IndexError):
        items.pop_front()

    items.push_back(1)
    items.push_back(2)

    assert items.pop_front() == 1
    assert items.pop_front() == 2
    assert items.is_empty()

    items.push_back(3)
    items.clear()
    assert len(items) == 0
    assert list(items) == []

    items.push_front(4)
    assert list(items) == [4]


def test_singly_linked_list_reverse():
    items: SinglyLinkedList[int] = SinglyLinkedList()
    items.reverse()
    assert list(items) == []

    for value in (1, 2, 3):
        items.push_back(value)

    items.reverse()
    assert list(items) == [3, 2, 1]

    items.push_back(0)
    assert list(items) == [3, 2, 1, 0]


def test_doubly_linked_list_backward_links_stay_consistent():
    items: DoublyLinkedList[int] = DoublyLinkedList()

    with pytest.raises(IndexError):
        items.pop_back()

    for value in (10, 20):
        items.push_back(value)

    items.push_front(5)
    items.insert_at(2, 15)
    assert list(reversed(items)) == [20, 15, 10, 5]

    items.remove(10)
    assert list(items) == [5, 15, 20]
    assert list(reversed(items)) == [20, 15, 5]

    assert items.pop_back() == 20
    assert items.pop_front() == 5
    assert list(items) == list(reversed(items)) == [15]

    assert items.pop_back() == 15
    assert items.is_empty()
    assert list(reversed(items)) == []


def test_linear_search():
    values = [10, 20, 30, 20]

    assert linear_search(values, 20) == 1
    assert linear_search(values, 99) == -1
    assert linear_search([], 1) == -1


def test_binary_search():
    values = [10, 20, 30, 40, 50]

    for index, value in enumerate(values):
        assert binary_search(values, value) == index

    for missing in (5, 35, 60):
        assert binary_search(values, missing) == -1

    assert binary_search([], 1) == -1


def test_dynamic_array_grows_and_shifts():
    array: DynamicArray[int] = DynamicArray(capacity=2)

    for value in (10, 20, 30):
        array.append(value)

    assert array.capacity == 4
    assert list(array) == [10, 20, 30]

    array.insert_at(1, 15)
    array.insert_at(0, 5)
    assert list(array) == [5, 10, 15, 20, 30]
    assert array.capacity == 8

    assert array.remove_at(0) == 5
    assert array.remove_at(len(array) - 1) == 30
    assert list(array) == [10, 15, 20]

    array[1] = 16
    assert array[1] == 16


def test_dynamic_array_rejects_invalid_indexes():
    array: DynamicArray[int] = DynamicArray()
    array.append(1)

    for index in (-1, 1):
        with pytest.raises(IndexError):
            array[index]
        with pytest.raises(IndexError):
            array.remove_at(index)

    with pytest.raises(IndexError):
        array.insert_at(2, 0)


def test_stack_and_queue_report_their_capacity():
    assert Stack(capacity=4).capacity == 4
    assert Queue(capacity=6).capacity == 6


def test_queue_clear_empties_it_and_keeps_it_usable():
    queue: Queue[int] = Queue(capacity=2)
    queue.enqueue(1)
    queue.dequeue()
    queue.enqueue(2)
    queue.enqueue(3)

    queue.clear()

    assert queue.is_empty()
    assert len(queue) == 0
    with pytest.raises(IndexError):
        queue.peek()

    queue.enqueue(5)
    queue.enqueue(6)

    assert queue.is_full()
    assert [queue.dequeue(), queue.dequeue()] == [5, 6]


@pytest.mark.parametrize("list_type", [SinglyLinkedList, DoublyLinkedList])
def test_linked_list_inserts_far_from_both_ends(list_type):
    items = list_type()

    for value in (10, 20, 30, 40, 50):
        items.push_back(value)

    items.insert_at(3, 35)
    items.insert_at(2, 25)

    assert list(items) == [10, 20, 25, 30, 35, 40, 50]
    assert len(items) == 7
