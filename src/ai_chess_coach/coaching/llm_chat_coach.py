"""LLM-backed conversational coach orchestration."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.coaching.llm_client import LLMClient
from ai_chess_coach.coaching.prompt_builder import PromptBuilder
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedPattern,
    VerifiedEvent,
    WeaknessProfile,
)


class LLMChatCoach:
    """Answers questions by sending grounded prompts to an injected LLM client."""

    def __init__(
        self,
        *,
        client: LLMClient,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        if not isinstance(client, LLMClient):
            raise TypeError("LLMChatCoach requires an LLMClient-compatible client.")
        if prompt_builder is not None and not isinstance(prompt_builder, PromptBuilder):
            raise TypeError("prompt_builder must be a PromptBuilder or None.")

        self._client = client
        self._prompt_builder = prompt_builder or PromptBuilder()

    def respond(
        self,
        question: str,
        *,
        coaching_moments: Iterable[CoachingMoment] = (),
        verified_events: Iterable[VerifiedEvent] = (),
        patterns: Iterable[DetectedPattern] = (),
        weakness_profile: WeaknessProfile | None = None,
    ) -> str:
        """Generate a response from supplied structured evidence."""

        prompt = self._prompt_builder.build(
            question,
            coaching_moments=coaching_moments,
            verified_events=verified_events,
            patterns=patterns,
            weakness_profile=weakness_profile,
        )

        return self._client.generate(prompt)
