"""Structured long-term player profile model."""

from __future__ import annotations

from dataclasses import dataclass

from ai_chess_coach.models.detected_pattern import DetectedPattern


@dataclass(frozen=True)
class WeaknessProfile:
    """Structured strengths, weaknesses, and recurring themes."""

    strengths: tuple[DetectedPattern, ...]
    weaknesses: tuple[DetectedPattern, ...]
    recurring_themes: tuple[DetectedPattern, ...]
