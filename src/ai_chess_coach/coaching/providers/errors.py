"""Shared errors for concrete LLM provider adapters."""


class LLMProviderError(RuntimeError):
    """Base error for LLM provider adapter failures."""


class MissingLLMApiKeyError(LLMProviderError):
    """Raised when a real provider client needs an API key and none is configured."""


class MissingLLMProviderDependencyError(LLMProviderError):
    """Raised when an optional provider SDK is not installed."""


class EmptyLLMResponseError(LLMProviderError):
    """Raised when a provider returns no usable text."""
