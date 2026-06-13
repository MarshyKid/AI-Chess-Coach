"""Aggregated pattern domain model."""

from __future__ import annotations

from dataclasses import dataclass

from ai_chess_coach.models.verified_event import VerifiedEvent


@dataclass(frozen=True)
class DetectedPattern:
    """Recurring theme aggregated from verified events."""

    pattern_type: str
    frequency: int
    severity: float
    supporting_events: tuple[VerifiedEvent, ...]
