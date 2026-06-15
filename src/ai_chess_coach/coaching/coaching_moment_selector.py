"""Select verified events for user-facing coaching moments."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ai_chess_coach.models import (
    EventPolarity,
    VerifiedEvent,
    get_event_type_metadata,
)


@dataclass(frozen=True)
class VerifiedEventGroup:
    """A selected group of related verified events."""

    events: tuple[VerifiedEvent, ...]
    category: str
    polarity: EventPolarity
    impact_magnitude: int


class CoachingMomentSelector:
    """Selects high-impact verified events for coaching review."""

    def __init__(
        self,
        *,
        min_impact_centipawns: int = 80,
        max_moments: int = 5,
    ) -> None:
        if min_impact_centipawns < 0:
            raise ValueError("min_impact_centipawns must be non-negative.")
        if max_moments < 0:
            raise ValueError("max_moments must be non-negative.")

        self.min_impact_centipawns = min_impact_centipawns
        self.max_moments = max_moments

    def select(self, events: Iterable[VerifiedEvent]) -> tuple[VerifiedEventGroup, ...]:
        """Return selected verified event groups in deterministic priority order."""

        selected_groups: list[VerifiedEventGroup] = []

        for event in events:
            if not isinstance(event, VerifiedEvent):
                raise TypeError("CoachingMomentSelector.select() accepts only VerifiedEvent objects.")

            event_type_metadata = get_event_type_metadata(event.event.event_type)
            if event_type_metadata.polarity == "neutral":
                continue

            impact_magnitude = event.engine_assessment.impact_magnitude
            if impact_magnitude is None or impact_magnitude < self.min_impact_centipawns:
                continue

            event_impact_for_side = event.engine_assessment.event_impact_for_side
            if event_impact_for_side is None:
                continue
            if (
                event_type_metadata.polarity == "positive"
                and event_impact_for_side <= 0
            ):
                continue
            if (
                event_type_metadata.polarity == "negative"
                and event_impact_for_side >= 0
            ):
                continue

            selected_groups.append(
                VerifiedEventGroup(
                    events=(event,),
                    category=event_type_metadata.category,
                    polarity=event_type_metadata.polarity,
                    impact_magnitude=impact_magnitude,
                )
            )

        return tuple(sorted(selected_groups, key=_sort_key)[: self.max_moments])


def _sort_key(
    group: VerifiedEventGroup,
) -> tuple[int, int, str, str, str, str, str, tuple[int, ...]]:
    first_event = group.events[0].event
    side_name = "white" if first_event.side else "black"

    return (
        -group.impact_magnitude,
        first_event.metadata.ply,
        side_name,
        group.category,
        group.polarity,
        first_event.event_type,
        first_event.metadata.move_uci,
        first_event.squares,
    )
