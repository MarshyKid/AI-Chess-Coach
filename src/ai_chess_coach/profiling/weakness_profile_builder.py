"""Build weakness profiles from detected patterns."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import DetectedPattern, WeaknessProfile

NEGATIVE_PATTERN_TYPES = frozenset(
    {
        "hanging_piece_created",
        "hanging_piece_ignored",
        "hanging_piece_lost",
        "fork_missed",
        "fork_allowed",
        "knight_outpost_missed",
    }
)

POSITIVE_PATTERN_TYPES = frozenset(
    {
        "fork_created",
        "knight_outpost_created",
    }
)


class WeaknessProfileBuilder:
    """Builds structured profiles from detected patterns."""

    def build(self, patterns: Iterable[DetectedPattern]) -> WeaknessProfile:
        sorted_patterns = _sorted_patterns(_validated_patterns(patterns))

        return WeaknessProfile(
            strengths=tuple(
                pattern
                for pattern in sorted_patterns
                if pattern.pattern_type in POSITIVE_PATTERN_TYPES
            ),
            weaknesses=tuple(
                pattern
                for pattern in sorted_patterns
                if pattern.pattern_type in NEGATIVE_PATTERN_TYPES
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
