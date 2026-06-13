"""Base detector contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_chess_coach.models import DetectedEvent, MoveTransition


class BaseDetector(ABC):
    """Abstract base class for deterministic chess concept detectors."""

    @abstractmethod
    def detect(self, transition: MoveTransition) -> list[DetectedEvent]:
        """Return machine-facing events detected for one move transition."""
