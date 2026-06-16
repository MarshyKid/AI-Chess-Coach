"""Policy for deciding whether verified events are user-facing coaching evidence."""

from __future__ import annotations

from ai_chess_coach.models import VerifiedEvent, get_event_type_metadata


class CoachingRelevancePolicy:
    """Filters verified events by event polarity and engine-confirmed impact."""

    def __init__(self, *, min_impact_centipawns: int = 80) -> None:
        if min_impact_centipawns < 0:
            raise ValueError("min_impact_centipawns must be non-negative.")

        self.min_impact_centipawns = min_impact_centipawns

    def is_relevant(self, event: VerifiedEvent) -> bool:
        """Return whether a verified event should influence user-facing outputs."""

        if not isinstance(event, VerifiedEvent):
            raise TypeError("CoachingRelevancePolicy.is_relevant() accepts only VerifiedEvent objects.")

        event_type_metadata = get_event_type_metadata(event.event.event_type)
        if event_type_metadata.polarity == "neutral":
            return False

        impact_magnitude = event.engine_assessment.impact_magnitude
        if impact_magnitude is None or impact_magnitude < self.min_impact_centipawns:
            return False

        event_impact_for_side = event.engine_assessment.event_impact_for_side
        if event_impact_for_side is None:
            return False
        if event_type_metadata.polarity == "positive":
            return event_impact_for_side > 0

        return event_impact_for_side < 0
