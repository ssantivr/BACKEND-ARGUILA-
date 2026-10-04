from collections.abc import Iterable

from app.data_structures import SinglyLinkedList
from app.models import AIMessage

MAX_CONTEXT_MESSAGES = 20


def build_context(
    messages: Iterable[AIMessage], content: str, limit: int = MAX_CONTEXT_MESSAGES
) -> list[dict[str, str]]:
    window: SinglyLinkedList[dict[str, str]] = SinglyLinkedList()

    for message in messages:
        window.push_back({"role": message.role, "content": message.content})

        if len(window) > limit:
            window.pop_front()

    while not window.is_empty() and next(iter(window))["role"] != "user":
        window.pop_front()

    window.push_back({"role": "user", "content": content})

    return list(window)
