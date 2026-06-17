"""Build weakness profiles from detected patterns."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import DetectedPattern, WeaknessProfile, get_event_type_metadata
from ai_chess_coach.relevance import CoachingRelevancePolicy, ExecutionStrengthPolicy


class WeaknessProfileBuilder:
    """Builds structured profiles from detected patterns."""

    def __init__(
        self,
        relevance_policy: CoachingRelevancePolicy | None = None,
        execution_strength_policy: ExecutionStrengthPolicy | None = None,
    ) -> None:
        self._relevance_policy = relevance_policy or CoachingRelevancePolicy()
        self._execution_strength_policy = (
            execution_strength_policy or ExecutionStrengthPolicy()
        )

    def build(self, patterns: Iterable[DetectedPattern]) -> WeaknessProfile:
        validated_patterns = _validated_patterns(patterns)
        profile_patterns = _profile_patterns(
            validated_patterns,
            self._relevance_policy,
        )
        execution_strength_patterns = _execution_strength_patterns(
            validated_patterns,
            self._relevance_policy,
            self._execution_strength_policy,
        )
        sorted_patterns = _sorted_patterns(profile_patterns)

        return WeaknessProfile(
            strengths=tuple(
                pattern
                for pattern in sorted_patterns
                if get_event_type_metadata(pattern.pattern_type).polarity == "positive"
            ),
            weaknesses=tuple(
                pattern
                for pattern in sorted_patterns
                if get_event_type_metadata(pattern.pattern_type).polarity == "negative"
            ),
            recurring_themes=tuple(sorted_patterns),
            execution_strengths=tuple(_sorted_patterns(execution_strength_patterns)),
        )


def _profile_patterns(
    patterns: list[DetectedPattern],
    relevance_policy: CoachingRelevancePolicy,
) -> list[DetectedPattern]:
    profile_patterns: list[DetectedPattern] = []

    for pattern in patterns:
        supporting_events = tuple(
            event
            for event in pattern.supporting_events
            if relevance_policy.is_relevant(event)
        )
        if not supporting_events:
            continue

        profile_patterns.append(
            DetectedPattern(
                pattern_type=pattern.pattern_type,
                frequency=len(supporting_events),
                severity=_average_profile_impact(supporting_events),
                supporting_events=supporting_events,
            )
        )

    return profile_patterns


def _execution_strength_patterns(
    patterns: list[DetectedPattern],
    relevance_policy: CoachingRelevancePolicy,
    execution_strength_policy: ExecutionStrengthPolicy,
) -> list[DetectedPattern]:
    execution_strength_patterns: list[DetectedPattern] = []

    for pattern in patterns:
        supporting_events = tuple(
            event
            for event in pattern.supporting_events
            if (
                execution_strength_policy.is_execution_strength(event)
                and not relevance_policy.is_relevant(event)
            )
        )
        if not supporting_events:
            continue

        execution_strength_patterns.append(
            DetectedPattern(
                pattern_type=pattern.pattern_type,
                frequency=len(supporting_events),
                severity=float(len(supporting_events)),
                supporting_events=supporting_events,
            )
        )

    return execution_strength_patterns


def _average_profile_impact(events) -> float:
    return float(
        sum(_profile_impact(event) for event in events)
        / len(events)
    )


def _profile_impact(event) -> int:
    if event.engine_assessment.event_score_kind == "mate":
        impact_rank = event.engine_assessment.impact_rank
        assert impact_rank is not None
        return impact_rank

    impact_magnitude = event.engine_assessment.impact_magnitude
    assert impact_magnitude is not None
    return impact_magnitude


def _validated_patterns(patterns: Iterable[DetectedPattern]) -> list[DetectedPattern]:
    validated_patterns: list[DetectedPattern] = []

    for pattern in patterns:
        if not isinstance(pattern, DetectedPattern):
            raise TypeError("WeaknessProfileBuilder.build() accepts only DetectedPattern objects.")

        validated_patterns.append(pattern)

    return validated_patterns


def _sorted_patterns(patterns: list[DetectedPattern]) -> list[DetectedPattern]:
    return sorted(
        patterns,
        key=lambda pattern: (-pattern.severity, -pattern.frequency, pattern.pattern_type),
    )
