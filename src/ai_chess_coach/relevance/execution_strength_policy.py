"""Policy for surfacing positive execution evidence in profiles."""

from __future__ import annotations

from ai_chess_coach.models import VerifiedEvent, get_event_type_metadata


class ExecutionStrengthPolicy:
    """Identifies verified positive execution events for profile evidence."""

    def is_execution_strength(self, event: VerifiedEvent) -> bool:
        """Return whether a verified event is non-contradicted execution evidence."""

        if not isinstance(event, VerifiedEvent):
            raise TypeError(
                "ExecutionStrengthPolicy.is_execution_strength() accepts only VerifiedEvent objects."
            )

        event_type_metadata = get_event_type_metadata(event.event.event_type)
        if event_type_metadata.polarity != "positive":
            return False
        if not event_type_metadata.is_execution_strength:
            return False

        assessment = event.engine_assessment
        if assessment.event_score_kind == "centipawn":
            event_impact = assessment.event_impact_for_side
            return event_impact is not None and event_impact >= 0
        if assessment.event_score_kind == "mate":
            event_impact = assessment.event_impact_rank_for_side
            return event_impact is not None and event_impact >= 0

        return False
