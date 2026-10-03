"""Client for the AI assistant (Claude, through the official Anthropic SDK).

Credentials come from the environment (ANTHROPIC_API_KEY); nothing is stored
in the repository. Without them the assistant endpoints answer 503.
"""

import os
from functools import lru_cache

import anthropic

from app.errors import AIUnavailableError

MODEL = "claude-opus-5-5"
MAX_OUTPUT_TOKENS = 16000
REQUEST_TIMEOUT_SECONDS = 120.0

REFUSAL_REPLY = "No puedo ayudar con esa solicitud."
EMPTY_REPLY = "No se obtuvo una respuesta. Intenta reformular la pregunta."


class AssistantClient:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(
            timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1
        )

    def reply(self, system: str, messages: list[dict[str, str]]) -> str:
        """Sends the conversation and returns the assistant's text."""
        try:
            response = self._client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=messages,
                # Thinking is adaptive by default on this model; effort is the
                # control for depth and cost.
                output_config={"effort": "medium"},
                # If a safety classifier declines the request, the API retries
                # it on a fallback model chosen by refusal category.
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
def _client() -> AssistantClient:
    return AssistantClient()


def get_assistant() -> AssistantClient:
    """FastAPI dependency. Tests override it with a fake."""
    if not (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    ):
        raise AIUnavailableError(
            "AI assistant is not configured: set ANTHROPIC_API_KEY on the server"
        )

    return _client()
