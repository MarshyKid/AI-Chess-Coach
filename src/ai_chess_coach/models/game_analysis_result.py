"""End-to-end game analysis result model."""

from __future__ import annotations

from dataclasses import dataclass

from ai_chess_coach.models.coaching_moment import CoachingMoment
from ai_chess_coach.models.detected_event import DetectedEvent
from ai_chess_coach.models.detected_pattern import DetectedPattern
from ai_chess_coach.models.move_transition import MoveTransition
from ai_chess_coach.models.verified_event import VerifiedEvent
from ai_chess_coach.models.weakness_profile import WeaknessProfile


@dataclass(frozen=True)
class GameAnalysisResult:
    """Structured output from analyzing one PGN game."""

    transitions: tuple[MoveTransition, ...]
    detected_events: tuple[DetectedEvent, ...]
    verified_events: tuple[VerifiedEvent, ...]
    detected_patterns: tuple[DetectedPattern, ...]
    weakness_profile: WeaknessProfile
    coaching_moments: tuple[CoachingMoment, ...]
