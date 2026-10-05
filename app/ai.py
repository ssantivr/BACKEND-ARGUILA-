import os
import re
import time
from functools import lru_cache
from typing import Protocol

import httpx

from app.errors import AIUnavailableError

REQUEST_TIMEOUT_SECONDS = 120.0
CONNECT_TIMEOUT_SECONDS = 1.0
RETRY_AFTER_SECONDS = 30.0
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
THINKING_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)

EMPTY_REPLY = "No se obtuvo una respuesta. Intenta reformular la pregunta."


class Assistant(Protocol):
    def reply(self, system: str, messages: list[dict[str, str]]) -> str: ...


class OllamaAssistant:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS)
        )
        self._unreachable_until = 0.0

    def _is_resting(self) -> bool:
        return time.monotonic() < self._unreachable_until

    def _rest(self) -> None:
        self._unreachable_until = time.monotonic() + RETRY_AFTER_SECONDS

    def reply(self, system: str, messages: list[dict[str, str]]) -> str:
        base_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")

        if self._is_resting():
            raise AIUnavailableError("Could not reach the local AI: start Ollama")

        try:
            response = self._client.post(
                f"{base_url}/api/chat",
                json={
                    "model": self._model(base_url),
                    "messages": [{"role": "system", "content": system}, *messages],
                    "stream": False,
                },
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
        except httpx.HTTPStatusError as error:
            raise AIUnavailableError(
                f"Local AI request failed (status {error.response.status_code})"
            ) from None
        except (httpx.ConnectError, httpx.ConnectTimeout):
            self._rest()
            raise AIUnavailableError("Could not reach the local AI: start Ollama") from None
        except httpx.HTTPError:
            raise AIUnavailableError("Could not reach the local AI: start Ollama") from None
        except (KeyError, TypeError, ValueError):
            raise AIUnavailableError("Local AI returned an unexpected answer") from None

        return THINKING_BLOCK.sub("", content).strip() or EMPTY_REPLY

    def _model(self, base_url: str) -> str:
        configured = os.environ.get("OLLAMA_MODEL")

        if configured:
            return configured

        response = self._client.get(f"{base_url}/api/tags")
        response.raise_for_status()
        models = response.json()["models"]

        if not models:
            raise AIUnavailableError("Local AI has no models: download one with 'ollama pull'")

        return models[0]["name"]

    def available_model(self) -> str | None:
        base_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")

        if self._is_resting():
            return None

        try:
            response = self._client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models = [model["name"] for model in response.json()["models"]]
        except (httpx.ConnectError, httpx.ConnectTimeout):
            self._rest()
            return None
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return None

        if not models:
            return None

        return os.environ.get("OLLAMA_MODEL") or models[0]


@lru_cache
def _local_client() -> OllamaAssistant:
    return OllamaAssistant()


def get_assistant() -> Assistant:
    return _local_client()


def get_assistant_status() -> dict[str, str | None]:
    model = _local_client().available_model()

    if model is not None:
        return {"provider": "ollama", "model": model}

    return {"provider": "rules", "model": None}


def get_optional_assistant() -> Assistant | None:
    try:
        return get_assistant()
    except AIUnavailableError:
        return None
