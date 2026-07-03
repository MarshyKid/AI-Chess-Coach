"""Deterministically build grounded coaching prompts from structured evidence.

The :class:`PromptBuilder` turns pre-selected, already-verified evidence into an
:class:`LLMPrompt`. It performs no chess analysis: it only formats evidence that
the deterministic backend already produced. Raw PGNs are never an input here.
"""

from __future__ import annotations

from collections.abc import Iterable
import re

import chess

from ai_chess_coach.coaching.evidence_formatter import (
    format_coaching_moment_details,
    format_supporting_event_detail,
)
from ai_chess_coach.coaching.llm_client import LLMPrompt
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedPattern,
    VerifiedEvent,
    WeaknessProfile,
)

SYSTEM_PROMPT = (
    "You are a chess coach who explains analysis that has already been verified "
    "by a separate engine and detection system.\n"
    "\n"
    "Rules:\n"
    "- Use only the evidence supplied in the user message. Do not add chess "
    "facts that are not present in that evidence.\n"
    "- Do not calculate moves, search variations, or evaluate positions "
    "yourself.\n"
    "- Do not analyze FEN strings or board positions independently; treat any "
    "position reference only as a label for evidence already given to you.\n"
    "- Do not claim a tactic, threat, or weakness exists unless the supplied "
    "evidence states it.\n"
    "- Do not ask for or rely on raw PGN move lists.\n"
    "- Do not call any move 'best' or 'winning' unless the supplied evidence "
    "says so.\n"
    "- If the evidence is insufficient to answer the question, say what is "
    "missing instead of guessing.\n"
    "- Be honest about uncertainty.\n"
    "- Treat the selected coaching moments as the primary teaching points and "
    "explain them in a clear, supportive coaching tone."
)

NO_EVIDENCE_MESSAGE = "No verified evidence was supplied."

_PGN_TAG_LINE = re.compile(r'^\s*\[[A-Za-z0-9_]+\s+"[^"]*"\]\s*$', re.MULTILINE)
_MOVE_NUMBER = re.compile(r"\b\d{1,3}\.")
_RAW_PGN_MOVE_NUMBER_THRESHOLD = 8


class PromptBuilder:
    """Builds deterministic, evidence-grounded coaching prompts."""

    def build(
        self,
        question: str,
        *,
        coaching_moments: Iterable[CoachingMoment] = (),
        verified_events: Iterable[VerifiedEvent] = (),
        patterns: Iterable[DetectedPattern] = (),
        weakness_profile: WeaknessProfile | None = None,
    ) -> LLMPrompt:
        """Build a grounded :class:`LLMPrompt` from selected structured evidence.

        Evidence is rendered in the order supplied; selection and ranking are the
        responsibility of upstream components (the selector and retriever), not
        this builder. Raw PGN move lists are never accepted: there is no PGN
        input path, and an obvious PGN blob in ``question`` raises ``ValueError``.
        """

        if _looks_like_raw_pgn(question):
            raise ValueError(
                "PromptBuilder does not accept raw PGN. Supply structured "
                "evidence (coaching moments, verified events, patterns, profile)."
            )

        moments = _as_tuple(coaching_moments, CoachingMoment, "coaching_moments")
        events = _as_tuple(verified_events, VerifiedEvent, "verified_events")
        retrieved_patterns = _as_tuple(patterns, DetectedPattern, "patterns")

        sections: list[str] = ["## PLAYER QUESTION", question.strip()]

        evidence_sections = _evidence_sections(
            moments, events, retrieved_patterns, weakness_profile
        )
        if evidence_sections:
            sections.extend(evidence_sections)
        else:
            sections.extend(["", NO_EVIDENCE_MESSAGE])

        return LLMPrompt(system=SYSTEM_PROMPT, user="\n".join(sections))


def _evidence_sections(
    moments: tuple[CoachingMoment, ...],
    events: tuple[VerifiedEvent, ...],
    patterns: tuple[DetectedPattern, ...],
    weakness_profile: WeaknessProfile | None,
) -> list[str]:
    sections: list[str] = []

    if moments:
        sections.extend(["", "## SELECTED COACHING MOMENTS"])
        for index, moment in enumerate(moments, start=1):
            sections.extend(_format_coaching_moment(index, moment))

    if weakness_profile is not None:
        sections.extend(["", "## WEAKNESS PROFILE"])
        sections.extend(_format_weakness_profile(weakness_profile))

    if patterns:
        sections.extend(["", "## RETRIEVED PATTERNS"])
        sections.extend(f"- {_format_pattern(pattern)}" for pattern in patterns)

    if events:
        sections.extend(["", "## SUPPORTING VERIFIED EVENTS"])
        for event in events:
            sections.append(f"- {_format_verified_event_header(event)}")
            sections.append(f"  {format_supporting_event_detail(event)}")

    return sections


def _format_coaching_moment(index: int, moment: CoachingMoment) -> list[str]:
    lines = [f"{index}. {moment.title}", f"   {moment.explanation}"]
    if moment.position_reference is not None:
        lines.append(f"   Position reference: {moment.position_reference}")
    if moment.highlights:
        lines.append(f"   Highlights: {_squares(moment.highlights)}")

    details = format_coaching_moment_details(moment)
    if details:
        lines.append("   Details:")
        lines.extend(f"     - {detail}" for detail in details)

    return lines


def _format_weakness_profile(profile: WeaknessProfile) -> list[str]:
    return [
        f"- High-impact strengths: {_pattern_summaries(profile.strengths)}",
        f"- Execution strengths: {_pattern_summaries(profile.execution_strengths)}",
        f"- Weaknesses: {_pattern_summaries(profile.weaknesses)}",
        f"- Recurring themes: {_pattern_summaries(profile.recurring_themes)}",
    ]


def _format_verified_event_header(event: VerifiedEvent) -> str:
    assessment = event.engine_assessment
    metadata = event.event.metadata
    parts = [
        event.event.event_type,
        f"move {metadata.move_san} ({metadata.move_uci})",
        f"ply {metadata.ply}",
        f"side {_side(event.event.side)}",
        f"score kind {assessment.event_score_kind}",
    ]

    if assessment.event_score_kind == "mate":
        parts.append(f"mate-aware rank impact {_optional(assessment.impact_rank)}")
    elif assessment.event_score_kind == "centipawn":
        parts.append(f"impact {_optional(assessment.impact_magnitude)} centipawns")

    if assessment.candidate_move_uci is not None:
        parts.append(f"candidate move {assessment.candidate_move_uci}")

    return "; ".join(parts)


def _format_pattern(pattern: DetectedPattern) -> str:
    return (
        f"{pattern.pattern_type} (frequency={pattern.frequency}, "
        f"severity={pattern.severity}, "
        f"supporting_events={len(pattern.supporting_events)})"
    )


def _pattern_summaries(patterns: tuple[DetectedPattern, ...]) -> str:
    if not patterns:
        return "none"

    return ", ".join(
        f"{pattern.pattern_type} (frequency={pattern.frequency}, "
        f"severity={pattern.severity})"
        for pattern in patterns
    )


def _looks_like_raw_pgn(text: str) -> bool:
    """Detect an obvious raw PGN blob without rejecting ordinary notation.

    A bracketed tag-pair header line (``[Event "..."]``) is an unambiguous PGN
    signal that never appears in a normal question. A very long run of move
    numbers is treated as a blob too. Short notation like ``1.e4 e5 Nf3`` in a
    question is intentionally allowed.
    """

    if _PGN_TAG_LINE.search(text):
        return True

    return len(_MOVE_NUMBER.findall(text)) >= _RAW_PGN_MOVE_NUMBER_THRESHOLD


def _as_tuple(values: Iterable[object], expected: type, name: str) -> tuple:
    items = tuple(values)
    for item in items:
        if not isinstance(item, expected):
            raise TypeError(f"{name} must contain only {expected.__name__} objects.")

    return items


def _side(side: chess.Color) -> str:
    return "white" if side == chess.WHITE else "black"


def _squares(squares: tuple[chess.Square, ...]) -> str:
    return ", ".join(chess.square_name(square) for square in squares)


def _optional(value: object) -> str:
    return "none" if value is None else str(value)
