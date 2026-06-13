"""Detector registration."""

from __future__ import annotations

from ai_chess_coach.detectors.base import BaseDetector


class DetectorRegistry:
    """Stores detectors in deterministic registration order."""

    def __init__(self) -> None:
        self._detectors: list[BaseDetector] = []

    def register(self, detector: BaseDetector) -> None:
        """Register a detector instance."""

        if not isinstance(detector, BaseDetector):
            raise TypeError("detector must be an instance of BaseDetector")

        self._detectors.append(detector)

    def registered_detectors(self) -> tuple[BaseDetector, ...]:
        """Return registered detectors in execution order."""

        return tuple(self._detectors)
