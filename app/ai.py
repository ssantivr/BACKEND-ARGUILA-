import os
from functools import lru_cache
from typing import Protocol

import anthropic

from app.errors import AIUnavailableError

MODEL = "claude-opus-5-5"
MAX_OUTPUT_TOKENS = 16000
REQUEST_TIMEOUT_SECONDS = 120.0

REFUSAL_REPLY = "No puedo ayudar con esa solicitud."
EMPTY_REPLY = "No se obtuvo una respuesta. Intenta reformular la pregunta."


class Assistant(Protocol):
    def reply(self, system: str, messages: list[dict[str, str]]) -> str: ...


class ClaudeAssistant:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(
            timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1
        )

    def reply(self, system: str, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=messages,
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            raise AIUnavailableError("AI assistant credentials were rejected") from None
        except anthropic.RateLimitError:
            raise AIUnavailableError("AI assistant is busy, try again shortly") from None
        except anthropic.APIStatusError as error:
            raise AIUnavailableError(
                f"AI assistant request failed (status {error.status_code})"
            ) from None
        except anthropic.APIConnectionError:
            raise AIUnavailableError("Could not reach the AI assistant") from None

        if response.stop_reason == "refusal":
            return REFUSAL_REPLY

        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        return text or EMPTY_REPLY


@lru_cache
def _client() -> ClaudeAssistant:
    return ClaudeAssistant()


def get_assistant() -> Assistant:
    if not (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    ):
        raise AIUnavailableError(
            "AI assistant is not configured: set ANTHROPIC_API_KEY on the server"
        )

    return _client()


def get_optional_assistant() -> Assistant | None:
    try:
        return get_assistant()
    except AIUnavailableError:
        return None
