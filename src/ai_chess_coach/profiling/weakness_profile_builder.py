"""Build weakness profiles from detected patterns."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import DetectedPattern, WeaknessProfile, get_event_type_metadata
from ai_chess_coach.relevance import CoachingRelevancePolicy


class WeaknessProfileBuilder:
    """Builds structured profiles from detected patterns."""

    def __init__(self, relevance_policy: CoachingRelevancePolicy | None = None) -> None:
        self._relevance_policy = relevance_policy or CoachingRelevancePolicy()

    def build(self, patterns: Iterable[DetectedPattern]) -> WeaknessProfile:
        profile_patterns = _profile_patterns(
            _validated_patterns(patterns),
            self._relevance_policy,
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
                severity=_average_impact_magnitude(supporting_events),
                supporting_events=supporting_events,
            )
        )

    return profile_patterns


def _average_impact_magnitude(events) -> float:
    return float(
        sum(event.engine_assessment.impact_magnitude for event in events)
        / len(events)
    )


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
