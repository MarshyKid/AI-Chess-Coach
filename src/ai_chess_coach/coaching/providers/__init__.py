"""Concrete LLM provider adapters."""

from ai_chess_coach.coaching.providers.errors import (
    EmptyLLMResponseError,
    LLMProviderError,
    MissingLLMApiKeyError,
    MissingLLMProviderDependencyError,
)
from ai_chess_coach.coaching.providers.ollama_client import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_BASE_URL_ENV_VAR,
    OLLAMA_MODEL_ENV_VAR,
    OllamaLLMClient,
    OllamaModelNotFoundError,
    OllamaProviderError,
    OllamaUnavailableError,
)
from ai_chess_coach.coaching.providers.openai_client import (
    DEFAULT_OPENAI_MODEL,
    OPENAI_API_KEY_ENV_VAR,
    OPENAI_MODEL_ENV_VAR,
    OpenAILLMClient,
)

__all__ = [
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_MODEL",
    "DEFAULT_OPENAI_MODEL",
    "OPENAI_API_KEY_ENV_VAR",
    "OPENAI_MODEL_ENV_VAR",
    "OLLAMA_BASE_URL_ENV_VAR",
    "OLLAMA_MODEL_ENV_VAR",
    "EmptyLLMResponseError",
    "LLMProviderError",
    "MissingLLMApiKeyError",
    "MissingLLMProviderDependencyError",
    "OllamaLLMClient",
    "OllamaModelNotFoundError",
    "OllamaProviderError",
    "OllamaUnavailableError",
    "OpenAILLMClient",
]
