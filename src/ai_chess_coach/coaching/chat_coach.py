"""Deterministic conversational coach over coaching moments."""

from __future__ import annotations

from collections.abc import Iterable
import re

from ai_chess_coach.models import CoachingMoment

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
NO_EVIDENCE_MESSAGE = "No coaching evidence is available yet."


class ChatCoach:
    """Answers questions using supplied coaching moments only."""

    def respond(self, question: str, moments: Iterable[CoachingMoment]) -> str:
        coaching_moments = _validated_moments(moments)
        if not coaching_moments:
            return NO_EVIDENCE_MESSAGE

        selected_moment = _select_moment(question, coaching_moments)
        return _format_response(selected_moment)


def _validated_moments(moments: Iterable[CoachingMoment]) -> list[CoachingMoment]:
    coaching_moments: list[CoachingMoment] = []

    for moment in moments:
        if not isinstance(moment, CoachingMoment):
            raise TypeError("ChatCoach.respond() accepts only CoachingMoment objects.")

        coaching_moments.append(moment)

    return coaching_moments


def _select_moment(question: str, moments: list[CoachingMoment]) -> CoachingMoment:
    question_tokens = _tokens(question)
    for moment in moments:
        if question_tokens & _tokens(moment.title):
            return moment

    return moments[0]


def _tokens(text: str) -> set[str]:
    return {_normalize_token(token) for token in TOKEN_PATTERN.findall(text.lower())}


def _normalize_token(token: str) -> str:
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]

    return token


def _format_response(moment: CoachingMoment) -> str:
    response_parts = [
        moment.title,
        "",
        moment.explanation,
    ]
    if moment.position_reference is not None:
        response_parts.extend(
            [
                "",
                f"Position: {moment.position_reference}",
            ]
        )

    return "\n".join(response_parts)
