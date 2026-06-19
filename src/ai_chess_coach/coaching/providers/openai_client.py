"""OpenAI-backed implementation of the LLMClient protocol."""

from __future__ import annotations

import os
from typing import Any

from ai_chess_coach.coaching.llm_client import LLMPrompt

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_MODEL_ENV_VAR = "AI_CHESS_COACH_OPENAI_MODEL"


class LLMProviderError(RuntimeError):
    """Base error for LLM provider adapter failures."""


class MissingLLMApiKeyError(LLMProviderError):
    """Raised when a real provider client needs an API key and none is configured."""


class MissingLLMProviderDependencyError(LLMProviderError):
    """Raised when an optional provider SDK is not installed."""


class EmptyLLMResponseError(LLMProviderError):
    """Raised when a provider returns no usable text."""


def _configured_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    return stripped


def _create_openai_client(api_key: str) -> object:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise MissingLLMProviderDependencyError(
            "OpenAI SDK is not installed. Install it with `uv sync --extra openai`."
        ) from exc

    return OpenAI(api_key=api_key)


class OpenAILLMClient:
    """OpenAI Responses API adapter for grounded LLMPrompt generation."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: object | None = None,
    ) -> None:
        self._model = (
            _configured_value(model)
            or _configured_value(os.environ.get(OPENAI_MODEL_ENV_VAR))
            or DEFAULT_OPENAI_MODEL
        )

        if client is not None:
            self._client = client
            return

        resolved_api_key = (
            _configured_value(api_key)
            or _configured_value(os.environ.get(OPENAI_API_KEY_ENV_VAR))
        )
        if resolved_api_key is None:
            raise MissingLLMApiKeyError(
                "OpenAI API key is required. Pass `api_key` or set OPENAI_API_KEY."
            )

        self._client = _create_openai_client(resolved_api_key)

    def generate(self, prompt: LLMPrompt) -> str:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=prompt.system,
                input=prompt.user,
            )
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError("OpenAI provider request failed.") from exc

        return self._extract_output_text(response)

    def _extract_output_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise EmptyLLMResponseError("OpenAI provider returned no output text.")

        return output_text
