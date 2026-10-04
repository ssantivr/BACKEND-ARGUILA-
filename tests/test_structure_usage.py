from types import SimpleNamespace

from app.data_structures import DynamicArray
from app.services.conversation_context import build_context
from app.services.material_ranking import rank_by_cost


def message(role: str, content: str) -> SimpleNamespace:
    return SimpleNamespace(role=role, content=content)


def material(name: str, quantity: float, unit_cost: float) -> SimpleNamespace:
    return SimpleNamespace(name=name, quantity=quantity, unit_cost=unit_cost)


def test_context_keeps_the_messages_in_order_and_adds_the_new_one():
    messages = [message("user", "a"), message("assistant", "b")]

    assert build_context(messages, "c") == [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]


def test_context_without_previous_messages_has_only_the_new_one():
    assert build_context([], "hello") == [{"role": "user", "content": "hello"}]


def test_context_drops_the_oldest_messages_beyond_the_limit():
    messages = [
        message("user" if index % 2 == 0 else "assistant", str(index)) for index in range(10)
    ]

    context = build_context(messages, "new", limit=4)

    assert [item["content"] for item in context] == ["6", "7", "8", "9", "new"]


def test_context_always_starts_with_a_user_message():
    messages = [
        message("user" if index % 2 == 0 else "assistant", str(index)) for index in range(6)
    ]

    context = build_context(messages, "new", limit=3)

    assert [item["content"] for item in context] == ["4", "5", "new"]
    assert context[0]["role"] == "user"


def test_rank_by_cost_orders_from_most_to_least_expensive():
    ranked = rank_by_cost(
        [
            material("Sand", 10, 2),
            material("Steel", 5, 100),
            material("Brick", 100, 1),
        ]
    )

    assert isinstance(ranked, DynamicArray)
    assert [item.name for item in ranked] == ["Steel", "Brick", "Sand"]
    assert ranked[0].name == "Steel"


def test_rank_by_cost_keeps_the_original_order_between_equal_costs():
    ranked = rank_by_cost([material("A", 2, 5), material("B", 1, 10), material("C", 5, 2)])

    assert [item.name for item in ranked] == ["A", "B", "C"]


def test_rank_by_cost_grows_past_the_initial_capacity_and_handles_no_materials():
    ranked = rank_by_cost([material(str(cost), 1, cost) for cost in range(10)])

    assert [item.unit_cost for item in ranked] == list(range(9, -1, -1))
    assert len(rank_by_cost([])) == 0
    assert not rank_by_cost([])
