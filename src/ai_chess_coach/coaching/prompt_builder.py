"""Build grounded provider-neutral prompts from structured evidence."""

from __future__ import annotations

from collections.abc import Iterable

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
    get_event_type_metadata,
)

SYSTEM_PROMPT = """You are a chess coach explaining verified evidence.
Use only the supplied structured evidence.
Do not calculate moves.
Do not analyze FENs independently.
Treat FENs and position references as identifiers only.
Do not infer material, threats, legal moves, board features, or tactics from a FEN.
Do not analyze raw PGNs.
Do not infer tactics or positional ideas not present in the evidence.
Do not claim a move is best unless the supplied evidence says so.
If Coaching Moments or a Weakness Profile are supplied, do not say there is no evidence.
Do not ask the user for more game context unless no structured evidence is supplied.
Base the answer mainly on Coaching Moments and Weakness Profile when they are supplied.
Do not mention empty optional retrieved sections as evidence absence.
If the evidence is insufficient, say what is missing.
Be clear about uncertainty.
Explain in a helpful coaching tone."""


class PromptBuilder:
    """Builds deterministic prompts from already selected or retrieved evidence."""

    def build(
        self,
        question: str,
        *,
        coaching_moments: Iterable[CoachingMoment] = (),
        verified_events: Iterable[VerifiedEvent] = (),
        patterns: Iterable[DetectedPattern] = (),
        weakness_profile: WeaknessProfile | None = None,
    ) -> LLMPrompt:
        """Return a grounded prompt for a provider-neutral LLM client."""

        if not isinstance(question, str):
            raise TypeError("PromptBuilder.build() question must be a string.")

        validated_moments = _validated_coaching_moments(coaching_moments)
        validated_events = _validated_verified_events(verified_events)
        validated_patterns = _validated_patterns(patterns)
        if weakness_profile is not None and not isinstance(weakness_profile, WeaknessProfile):
            raise TypeError(
                "PromptBuilder.build() weakness_profile must be a WeaknessProfile or None."
            )

        return LLMPrompt(
            system=SYSTEM_PROMPT,
            user=_user_prompt(
                question,
                coaching_moments=validated_moments,
                verified_events=validated_events,
                patterns=validated_patterns,
                weakness_profile=weakness_profile,
            ),
        )


def _validated_coaching_moments(
    coaching_moments: Iterable[CoachingMoment],
) -> tuple[CoachingMoment, ...]:
    validated: list[CoachingMoment] = []
    try:
        iterator = iter(coaching_moments)
    except TypeError as exc:
        raise TypeError(
            "PromptBuilder.build() coaching_moments must be an iterable of CoachingMoment objects."
        ) from exc

    for moment in iterator:
        if not isinstance(moment, CoachingMoment):
            raise TypeError(
                "PromptBuilder.build() coaching_moments accepts only CoachingMoment objects."
            )

        validated.append(moment)

    return tuple(validated)


def _validated_verified_events(
    verified_events: Iterable[VerifiedEvent],
) -> tuple[VerifiedEvent, ...]:
    validated: list[VerifiedEvent] = []
    try:
        iterator = iter(verified_events)
    except TypeError as exc:
        raise TypeError(
            "PromptBuilder.build() verified_events must be an iterable of VerifiedEvent objects."
        ) from exc

    for event in iterator:
        if not isinstance(event, VerifiedEvent):
            raise TypeError(
                "PromptBuilder.build() verified_events accepts only VerifiedEvent objects."
            )

        validated.append(event)

    return tuple(validated)


def _validated_patterns(
    patterns: Iterable[DetectedPattern],
) -> tuple[DetectedPattern, ...]:
    validated: list[DetectedPattern] = []
    try:
        iterator = iter(patterns)
    except TypeError as exc:
        raise TypeError(
            "PromptBuilder.build() patterns must be an iterable of DetectedPattern objects."
        ) from exc

    for pattern in iterator:
        if not isinstance(pattern, DetectedPattern):
            raise TypeError(
                "PromptBuilder.build() patterns accepts only DetectedPattern objects."
            )

        validated.append(pattern)

    return tuple(validated)


def _user_prompt(
    question: str,
    *,
    coaching_moments: tuple[CoachingMoment, ...],
    verified_events: tuple[VerifiedEvent, ...],
    patterns: tuple[DetectedPattern, ...],
    weakness_profile: WeaknessProfile | None,
) -> str:
    has_evidence = bool(
        coaching_moments
        or weakness_profile is not None
        or patterns
        or verified_events
    )
    sections = [
        _section("User Question", question),
        _section("Evidence Status", _evidence_status_text(has_evidence)),
        _section("Coaching Moments", _coaching_moments_text(coaching_moments)),
    ]

    if weakness_profile is not None:
        sections.append(_section("Weakness Profile", _weakness_profile_text(weakness_profile)))
    if patterns:
        sections.append(_section("Retrieved Patterns", _patterns_text(patterns)))
    if verified_events:
        sections.append(_section("Retrieved Verified Events", _verified_events_text(verified_events)))

    return "\n\n".join(sections)


def _section(title: str, content: str) -> str:
    return f"## {title}\n{content}"


def _evidence_status_text(has_evidence: bool) -> str:
    if not has_evidence:
        return "No structured evidence supplied. Say what evidence is missing."

    return (
        "Structured evidence is supplied. Base your answer on the supplied "
        "Coaching Moments and Weakness Profile. Empty optional retrieved sections "
        "do not mean there is no evidence."
    )


def _coaching_moments_text(moments: tuple[CoachingMoment, ...]) -> str:
    if not moments:
        return "None supplied."

    return "\n".join(
        _numbered_item(index, _coaching_moment_text(moment))
        for index, moment in enumerate(moments, start=1)
    )


def _coaching_moment_text(moment: CoachingMoment) -> str:
    lines = [
        moment.title,
        f"Explanation: {moment.explanation}",
        f"Position reference only, do not analyze as FEN: {_value(moment.position_reference)}",
        f"Highlights: {_squares(moment.highlights)}",
    ]
    details = format_coaching_moment_details(moment)
    if details:
        lines.append("Supporting details:")
        lines.extend(f"- {detail}" for detail in details)
    else:
        lines.append("Supporting details: none")

    return "\n".join(lines)


def _weakness_profile_text(profile: WeaknessProfile | None) -> str:
    if profile is None:
        return "None supplied."

    return "\n".join(
        [
            f"High-impact strengths: {_pattern_list(profile.strengths)}",
            f"Execution strengths: {_pattern_list(profile.execution_strengths)}",
            f"Weaknesses: {_pattern_list(profile.weaknesses)}",
            f"Recurring themes: {_pattern_list(profile.recurring_themes)}",
        ]
    )


def _patterns_text(patterns: tuple[DetectedPattern, ...]) -> str:
    if not patterns:
        return "None supplied."

    return "\n".join(
        _numbered_item(index, _pattern_text(pattern))
        for index, pattern in enumerate(patterns, start=1)
    )


def _pattern_list(patterns: tuple[DetectedPattern, ...]) -> str:
    if not patterns:
        return "none"

    return "; ".join(_pattern_text(pattern) for pattern in patterns)


def _pattern_text(pattern: DetectedPattern) -> str:
    metadata = get_event_type_metadata(pattern.pattern_type)
    return (
        f"{metadata.display_name} ({pattern.pattern_type}): "
        f"frequency={pattern.frequency}, severity={pattern.severity}, "
        f"supporting_events={len(pattern.supporting_events)}"
    )


def _verified_events_text(events: tuple[VerifiedEvent, ...]) -> str:
    if not events:
        return "None supplied."

    return "\n".join(
        _numbered_item(index, _verified_event_text(event))
        for index, event in enumerate(events, start=1)
    )


def _verified_event_text(event: VerifiedEvent) -> str:
    detected_event = event.event
    metadata = get_event_type_metadata(detected_event.event_type)
    lines = [
        f"{metadata.display_name} ({detected_event.event_type})",
        f"Side: {_side(detected_event.side)}",
        f"Ply: {detected_event.metadata.ply}",
        f"Move: {detected_event.metadata.move_san} ({detected_event.metadata.move_uci})",
        f"Squares: {_squares(detected_event.squares)}",
        f"Score kind: {event.engine_assessment.event_score_kind}",
        _impact_text(event),
        f"Candidate move: {_candidate_move_text(event)}",
        f"Detail: {format_supporting_event_detail(event)}",
    ]

    return "\n".join(lines)


def _impact_text(event: VerifiedEvent) -> str:
    assessment = event.engine_assessment
    if assessment.event_score_kind == "mate":
        return f"Mate-aware rank impact: {_value(assessment.impact_rank)}"
    if assessment.event_score_kind == "centipawn":
        return f"Centipawn impact: {_value(assessment.impact_magnitude)} centipawns"

    return "Verified impact: unavailable"


def _candidate_move_text(event: VerifiedEvent) -> str:
    candidate = event.event.candidate_move
    if candidate is None:
        return "none"

    san = candidate.move_san if candidate.move_san is not None else "none"
    return f"{san} ({candidate.move_uci}), side={_side(candidate.side)}"


def _numbered_item(index: int, text: str) -> str:
    return f"{index}. {text}"


def _side(side: chess.Color) -> str:
    return "white" if side == chess.WHITE else "black"


def _squares(squares: tuple[chess.Square, ...]) -> str:
    if not squares:
        return "none"

    return ", ".join(chess.square_name(square) for square in squares)


def _value(value: object) -> str:
    if value is None:
        return "none"

    return str(value)
