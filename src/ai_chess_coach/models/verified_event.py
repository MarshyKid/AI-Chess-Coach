"""Verified detector event domain model."""

from __future__ import annotations

from dataclasses import dataclass

from ai_chess_coach.models.detected_event import DetectedEvent
from ai_chess_coach.models.engine_assessment import EngineAssessment


@dataclass(frozen=True)
class VerifiedEvent:
    """Detected event with attached objective engine evidence."""

    event: DetectedEvent
    engine_assessment: EngineAssessment
