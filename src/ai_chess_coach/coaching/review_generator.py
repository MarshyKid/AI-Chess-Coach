"""Generate deterministic coaching moments from verified events."""

from __future__ import annotations

from collections.abc import Iterable

import chess

from ai_chess_coach.coaching.coaching_moment_selector import (
    CoachingMomentSelector,
    VerifiedEventGroup,
)
from ai_chess_coach.models import CoachingMoment, VerifiedEvent


class ReviewGenerator:
    """Formats verified events as simple coaching moments."""

    def __init__(self, selector: CoachingMomentSelector | None = None) -> None:
        self._selector = selector or CoachingMomentSelector()

    def generate(self, events: Iterable[VerifiedEvent]) -> tuple[CoachingMoment, ...]:
        groups = self._selector.select(events)

        return tuple(_coaching_moment(group) for group in groups)


def _coaching_moment(group: VerifiedEventGroup) -> CoachingMoment:
    return CoachingMoment(
        title=_title(group),
        explanation=_explanation(group),
        supporting_evidence=group.events,
        position_reference=_position_reference(group),
        highlights=_highlights(group),
    )


def _title(group: VerifiedEventGroup) -> str:
    if len(group.events) == 1:
        return group.events[0].event.event_type.replace("_", " ").title()

    category_title = group.category.replace("_", " ").title()
    polarity_title = group.polarity.title()
    ply = group.events[0].event.metadata.ply
    return f"{category_title} {polarity_title} Events On Ply {ply}"


def _explanation(group: VerifiedEventGroup) -> str:
    if len(group.events) > 1:
        return (
            f"{len(group.events)} related {group.category.replace('_', ' ')} "
            f"{group.polarity} events were selected with impact up to "
            f"{group.impact_magnitude} centipawns."
        )

    event = group.events[0]
    event_title = event.event.event_type.replace("_", " ").title()
    eval_delta = event.engine_assessment.eval_delta
    if eval_delta is not None:
        return f"{event_title} was verified with an engine evaluation change of {eval_delta} centipawns."

    return f"{event_title} was detected with detector severity {event.event.severity}."


def _position_reference(group: VerifiedEventGroup) -> str:
    return group.events[0].event.metadata.after_fen


def _highlights(group: VerifiedEventGroup) -> tuple[chess.Square, ...]:
    highlighted_squares = {
        square
        for event in group.events
        for square in event.event.squares
    }

    return tuple(
        square
        for square in chess.SQUARES
        if square in highlighted_squares
    )
