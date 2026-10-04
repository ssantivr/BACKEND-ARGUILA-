import time
from collections.abc import Callable

from app.data_structures import (
    DoublyLinkedList,
    DynamicArray,
    Queue,
    SinglyLinkedList,
    Stack,
    binary_search,
    linear_search,
)

SIZES = (1_000, 10_000, 100_000)
ROUNDS = 5
REPEATS = 200

Measure = Callable[[int], float]


def best_of(action: Callable[[], None], operations: int) -> float:
    best = float("inf")

    for _ in range(ROUNDS):
        started = time.perf_counter_ns()
        action()
        best = min(best, time.perf_counter_ns() - started)

    return best / operations / 1000


def filled_array(size: int) -> DynamicArray[int]:
    array: DynamicArray[int] = DynamicArray()

    for value in range(size):
        array.append(value)

    return array


def filled_list(list_type: type, size: int):
    items = list_type()

    for value in range(size):
        items.push_back(value)

    return items


def array_append(size: int) -> float:
    return best_of(lambda: filled_array(size), size)


def array_index(size: int) -> float:
    array = filled_array(size)
    middle = size // 2

    def action() -> None:
        for _ in range(REPEATS):
            array[middle]

    return best_of(action, REPEATS)


def array_insert_front(size: int) -> float:
    array = filled_array(size)

    def action() -> None:
        for _ in range(REPEATS):
            array.insert_at(0, -1)

        for _ in range(REPEATS):
            array.remove_at(0)

    return best_of(action, REPEATS * 2)


def search_linear(size: int) -> float:
    values = list(range(size))

    def action() -> None:
        for _ in range(REPEATS):
            linear_search(values, -1)

    return best_of(action, REPEATS)


def search_binary(size: int) -> float:
    values = list(range(size))

    def action() -> None:
        for _ in range(REPEATS):
            binary_search(values, -1)

    return best_of(action, REPEATS)


def stack_push_pop(size: int) -> float:
    def action() -> None:
        stack: Stack[int] = Stack(capacity=size)

        for value in range(size):
            stack.push(value)

        for _ in range(size):
            stack.pop()

    return best_of(action, size * 2)


def queue_enqueue_dequeue(size: int) -> float:
    def action() -> None:
        queue: Queue[int] = Queue(capacity=size)

        for value in range(size):
            queue.enqueue(value)

        for _ in range(size):
            queue.dequeue()

    return best_of(action, size * 2)


def list_push_back(list_type: type) -> Measure:
    return lambda size: best_of(lambda: filled_list(list_type, size), size)


def list_push_pop_front(list_type: type) -> Measure:
    def measure(size: int) -> float:
        items = filled_list(list_type, size)

        def action() -> None:
            for _ in range(REPEATS):
                items.push_front(-1)

            for _ in range(REPEATS):
                items.pop_front()

        return best_of(action, REPEATS * 2)

    return measure


def list_search(list_type: type) -> Measure:
    def measure(size: int) -> float:
        items = filled_list(list_type, size)
        repeats = 20

        def action() -> None:
            for _ in range(repeats):
                items.__contains__(-1)

        return best_of(action, repeats)

    return measure


def list_insert_middle(list_type: type) -> Measure:
    def measure(size: int) -> float:
        items = filled_list(list_type, size)
        repeats = 20
        middle = size // 2

        def action() -> None:
            for _ in range(repeats):
                items.insert_at(middle, -1)

        return best_of(action, repeats)

    return measure


def doubly_push_pop_back(size: int) -> float:
    items = filled_list(DoublyLinkedList, size)

    def action() -> None:
        for _ in range(REPEATS):
            items.push_back(-1)

        for _ in range(REPEATS):
            items.pop_back()

    return best_of(action, REPEATS * 2)


CASES: list[tuple[str, str, str, Measure]] = [
    ("Array dinámico", "Agregar al final", "O(1) amortizado", array_append),
    ("Array dinámico", "Acceso por índice", "O(1)", array_index),
    ("Array dinámico", "Insertar y eliminar al inicio", "O(n)", array_insert_front),
    ("Array", "Búsqueda lineal", "O(n)", search_linear),
    ("Array", "Búsqueda binaria", "O(log n)", search_binary),
    ("Stack", "Push y pop", "O(1)", stack_push_pop),
    ("Queue", "Enqueue y dequeue", "O(1)", queue_enqueue_dequeue),
    ("Lista simple", "Insertar al final", "O(1)", list_push_back(SinglyLinkedList)),
    (
        "Lista simple",
        "Insertar y eliminar al inicio",
        "O(1)",
        list_push_pop_front(SinglyLinkedList),
    ),
    ("Lista simple", "Buscar un valor", "O(n)", list_search(SinglyLinkedList)),
    ("Lista simple", "Insertar en el medio", "O(n)", list_insert_middle(SinglyLinkedList)),
    ("Lista doble", "Insertar al final", "O(1)", list_push_back(DoublyLinkedList)),
    ("Lista doble", "Insertar y eliminar al final", "O(1)", doubly_push_pop_back),
    ("Lista doble", "Buscar un valor", "O(n)", list_search(DoublyLinkedList)),
    ("Lista doble", "Insertar en el medio", "O(n)", list_insert_middle(DoublyLinkedList)),
]


def format_time(microseconds: float) -> str:
    if microseconds >= 100:
        return f"{microseconds:.0f}"

    if microseconds >= 10:
        return f"{microseconds:.1f}"

    return f"{microseconds:.2f}"


def main() -> None:
    headers = [f"n = {size:,}".replace(",", " ") for size in SIZES]

    print("| Estructura | Operación | Esperado | " + " | ".join(headers) + " | Crece |")
    print("|---|---|---|" + "---:|" * (len(SIZES) + 1))

    for structure, operation, expected, measure in CASES:
        times = [measure(size) for size in SIZES]
        growth = times[-1] / times[0]
        cells = " | ".join(format_time(value) for value in times)

        print(f"| {structure} | {operation} | {expected} | {cells} | ×{growth:.1f} |")


if __name__ == "__main__":
    main()
