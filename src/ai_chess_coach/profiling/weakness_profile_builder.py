"""Build weakness profiles from detected patterns."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import DetectedPattern, WeaknessProfile, get_event_type_metadata


class WeaknessProfileBuilder:
    """Builds structured profiles from detected patterns."""

    def build(self, patterns: Iterable[DetectedPattern]) -> WeaknessProfile:
        sorted_patterns = _sorted_patterns(_validated_patterns(patterns))

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
