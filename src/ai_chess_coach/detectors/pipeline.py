"""Detection pipeline orchestration."""

from __future__ import annotations

from ai_chess_coach.detectors.registry import DetectorRegistry
from ai_chess_coach.models import DetectedEvent, MoveTransition


class DetectionPipeline:
    """Runs registered detectors over a move transition."""

    def __init__(self, registry: DetectorRegistry) -> None:
        self._registry = registry

    def run(self, transition: MoveTransition) -> list[DetectedEvent]:
        """Run every registered detector and combine their events."""

        events: list[DetectedEvent] = []
        for detector in self._registry.registered_detectors():
            events.extend(detector.detect(transition))

        return events
