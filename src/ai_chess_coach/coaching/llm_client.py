"""Provider-agnostic LLM boundary for evidence-grounded coaching.

This module defines the seam between the deterministic chess analysis backend
and any future language-model provider. It intentionally has no provider SDK,
no network access, and no chess logic: a concrete client (added in a later
task) implements :class:`LLMClient` to turn an :class:`LLMPrompt` into text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMPrompt:
    """An immutable, provider-agnostic prompt.

    The prompt is split into a ``system`` section (grounding instructions and
    coaching persona) and a ``user`` section (the player question plus clearly
    labeled, pre-selected evidence). Keeping the two separate maps cleanly onto
    provider APIs that distinguish system from user messages and lets tests
    assert each section independently.
    """

    system: str
    user: str


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic text-generation contract.

    Implementations receive a fully built :class:`LLMPrompt` and return the
    model's text response. The protocol is intentionally tiny so it can be
    satisfied by a fake in unit tests without any network or API dependency.
    """

    def generate(self, prompt: LLMPrompt) -> str:
        """Return a text response for ``prompt``."""
        ...
