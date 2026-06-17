"""Retrieve relevant verified evidence for coaching layers."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import DetectedPattern, VerifiedEvent, WeaknessProfile


class EvidenceRetriever:
    """Deterministic in-memory retrieval over existing evidence objects."""

    def retrieve_events(
        self,
        events: Iterable[VerifiedEvent],
        *,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> tuple[VerifiedEvent, ...]:
        _validate_limit(limit)
        verified_events = _validated_events(events)
        if event_type is not None:
            verified_events = [
                event for event in verified_events if event.event.event_type == event_type
            ]

        return tuple(sorted(verified_events, key=_event_sort_key)[:limit])

    def retrieve_patterns(
        self,
        patterns: Iterable[DetectedPattern],
        *,
        pattern_type: str | None = None,
        limit: int | None = None,
    ) -> tuple[DetectedPattern, ...]:
        _validate_limit(limit)
        detected_patterns = _validated_patterns(patterns)
        if pattern_type is not None:
            detected_patterns = [
                pattern
                for pattern in detected_patterns
                if pattern.pattern_type == pattern_type
            ]

        return tuple(sorted(detected_patterns, key=_pattern_sort_key)[:limit])

    def retrieve_profile(
        self,
        profile: WeaknessProfile,
        *,
        include_strengths: bool = True,
        include_execution_strengths: bool = True,
        include_weaknesses: bool = True,
        include_recurring_themes: bool = True,
        limit: int | None = None,
    ) -> tuple[DetectedPattern, ...]:
        _validate_limit(limit)
        if not isinstance(profile, WeaknessProfile):
            raise TypeError("EvidenceRetriever.retrieve_profile() accepts only WeaknessProfile objects.")

        patterns: list[DetectedPattern] = []
        if include_strengths:
            patterns.extend(profile.strengths)
        if include_execution_strengths:
            patterns.extend(profile.execution_strengths)
        if include_weaknesses:
            patterns.extend(profile.weaknesses)
        if include_recurring_themes:
            patterns.extend(profile.recurring_themes)

        deduplicated_patterns = _deduplicate_by_identity(patterns)
        return tuple(sorted(deduplicated_patterns, key=_pattern_sort_key)[:limit])


def _validate_limit(limit: int | None) -> None:
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative.")


def _validated_events(events: Iterable[VerifiedEvent]) -> list[VerifiedEvent]:
    verified_events: list[VerifiedEvent] = []
    for event in events:
        if not isinstance(event, VerifiedEvent):
            raise TypeError("EvidenceRetriever.retrieve_events() accepts only VerifiedEvent objects.")

        verified_events.append(event)

    return verified_events


def _validated_patterns(patterns: Iterable[DetectedPattern]) -> list[DetectedPattern]:
    detected_patterns: list[DetectedPattern] = []
    for pattern in patterns:
        if not isinstance(pattern, DetectedPattern):
            raise TypeError("EvidenceRetriever.retrieve_patterns() accepts only DetectedPattern objects.")

        detected_patterns.append(pattern)

    return detected_patterns


def _event_sort_key(event: VerifiedEvent) -> tuple[float, str, str]:
    eval_delta = event.engine_assessment.eval_delta
    score = abs(eval_delta) if eval_delta is not None else event.event.severity

    return (
        -float(score),
        event.event.event_type,
        event.event.move.uci(),
    )


def _pattern_sort_key(pattern: DetectedPattern) -> tuple[float, int, str]:
    return (
        -pattern.severity,
        -pattern.frequency,
        pattern.pattern_type,
    )


def _deduplicate_by_identity(patterns: list[DetectedPattern]) -> list[DetectedPattern]:
    seen_ids: set[int] = set()
    deduplicated_patterns: list[DetectedPattern] = []

    for pattern in patterns:
        pattern_id = id(pattern)
        if pattern_id in seen_ids:
            continue

        seen_ids.add(pattern_id)
        deduplicated_patterns.append(pattern)

    return deduplicated_patterns
