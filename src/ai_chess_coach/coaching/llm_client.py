"""Provider-agnostic LLM prompt and client boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMPrompt:
    """Structured prompt with provider-neutral message roles."""

    system: str
    user: str


@runtime_checkable
class LLMClient(Protocol):
    """Provider-neutral text generation interface."""

    def generate(self, prompt: LLMPrompt) -> str:
        """Generate text from a grounded prompt."""
