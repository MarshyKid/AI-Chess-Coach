"""Ollama-backed implementation of the LLMClient protocol."""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
import urllib.error
import urllib.request

from ai_chess_coach.coaching.llm_client import LLMPrompt
from ai_chess_coach.coaching.providers.errors import (
    EmptyLLMResponseError,
    LLMProviderError,
)

DEFAULT_OLLAMA_MODEL = "llama3.2:3b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL_ENV_VAR = "AI_CHESS_COACH_OLLAMA_MODEL"
OLLAMA_BASE_URL_ENV_VAR = "AI_CHESS_COACH_OLLAMA_BASE_URL"


class OllamaProviderError(LLMProviderError):
    """Base error for Ollama provider adapter failures."""


class OllamaUnavailableError(OllamaProviderError):
    """Raised when the local Ollama service is unavailable."""


class OllamaModelNotFoundError(OllamaProviderError):
    """Raised when Ollama reports that the configured model is unavailable."""


def _configured_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    return stripped


def _configured_base_url(value: str | None) -> str | None:
    configured = _configured_value(value)
    if configured is None:
        return None

    return configured.rstrip("/")


def _error_message(response: Mapping[str, object] | None, fallback: str) -> str:
    if response is None:
        return fallback

    error = response.get("error")
    if isinstance(error, str) and error.strip():
        return error

    return fallback


def _looks_like_missing_model(status_code: int, message: str) -> bool:
    lower_message = message.lower()
    return status_code == 404 or (
        "model" in lower_message
        and any(term in lower_message for term in ("not found", "pull", "missing"))
    )


class _UrllibJsonClient:
    def post_json(self, url: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            _raise_http_error(exc.code, body)
        except urllib.error.URLError as exc:
            raise OllamaUnavailableError(
                "Ollama is unavailable. Confirm `ollama serve` is running."
            ) from exc
        except OSError as exc:
            raise OllamaUnavailableError(
                "Ollama is unavailable. Confirm `ollama serve` is running."
            ) from exc

        return _decode_json_mapping(body)


def _decode_json_mapping(body: str) -> Mapping[str, object]:
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OllamaProviderError("Ollama returned invalid JSON.") from exc

    if not isinstance(decoded, dict):
        raise OllamaProviderError("Ollama returned malformed JSON.")

    return decoded


def _raise_http_error(status_code: int, body: str) -> None:
    response: Mapping[str, object] | None = None
    if body:
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            response = decoded

    message = _error_message(response, f"Ollama request failed with HTTP {status_code}.")
    if _looks_like_missing_model(status_code, message):
        raise OllamaModelNotFoundError(
            f"Ollama model is unavailable: {message}"
        )

    raise OllamaProviderError(message)


class OllamaLLMClient:
    """Ollama local chat API adapter for grounded LLMPrompt generation."""

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        client: object | None = None,
    ) -> None:
        self._model = (
            _configured_value(model)
            or _configured_value(os.environ.get(OLLAMA_MODEL_ENV_VAR))
            or DEFAULT_OLLAMA_MODEL
        )
        self._base_url = (
            _configured_base_url(base_url)
            or _configured_base_url(os.environ.get(OLLAMA_BASE_URL_ENV_VAR))
            or DEFAULT_OLLAMA_BASE_URL
        )
        self._client = client or _UrllibJsonClient()

    def generate(self, prompt: LLMPrompt) -> str:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "stream": False,
        }

        try:
            response = self._client.post_json(f"{self._base_url}/api/chat", payload)
        except (OllamaProviderError, EmptyLLMResponseError):
            raise
        except urllib.error.URLError as exc:
            raise OllamaUnavailableError(
                "Ollama is unavailable. Confirm `ollama serve` is running."
            ) from exc
        except OSError as exc:
            raise OllamaUnavailableError(
                "Ollama is unavailable. Confirm `ollama serve` is running."
            ) from exc
        except Exception as exc:
            raise OllamaProviderError("Ollama provider request failed.") from exc

        return self._extract_message_content(response)

    def _extract_message_content(self, response: Mapping[str, object]) -> str:
        error = response.get("error")
        if isinstance(error, str) and error.strip():
            if _looks_like_missing_model(0, error):
                raise OllamaModelNotFoundError(
                    f"Ollama model is unavailable: {error}"
                )
            raise OllamaProviderError(error)

        message = response.get("message")
        if not isinstance(message, dict):
            raise OllamaProviderError("Ollama returned no message content.")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise EmptyLLMResponseError("Ollama returned no output text.")

        return content
