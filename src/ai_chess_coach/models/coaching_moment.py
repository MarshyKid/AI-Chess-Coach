"""User-facing coaching moment domain model."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from ai_chess_coach.models.detected_pattern import DetectedPattern
from ai_chess_coach.models.verified_event import VerifiedEvent
from ai_chess_coach.models.weakness_profile import WeaknessProfile


@dataclass(frozen=True)
class CoachingMoment:
    """User-facing lesson grounded in structured evidence."""

    title: str
    explanation: str
    supporting_evidence: tuple[VerifiedEvent | DetectedPattern | WeaknessProfile, ...]
    position_reference: str | None
    highlights: tuple[chess.Square, ...]
