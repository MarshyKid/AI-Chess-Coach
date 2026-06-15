"""Generate deterministic coaching moments from verified events."""

from __future__ import annotations

from collections.abc import Iterable

import chess

from ai_chess_coach.coaching.coaching_moment_selector import (
    CoachingMomentSelector,
    VerifiedEventGroup,
)
from ai_chess_coach.models import CoachingMoment, VerifiedEvent, get_event_type_metadata


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
    move_number = _move_number(group)
    if len(group.events) == 1:
        event_type = group.events[0].event.event_type
        metadata = get_event_type_metadata(event_type)
        if event_type.startswith("fork_"):
            return f"Move {move_number}: Fork-related tactical issue"
        if event_type.startswith("hanging_piece_"):
            return f"Move {move_number}: Piece safety issue"
        if event_type.startswith("knight_outpost_"):
            return f"Move {move_number}: Knight outpost opportunity"

        return f"Move {move_number}: {metadata.display_name}"

    if _all_event_types_start_with(group, "fork_"):
        return f"Move {move_number}: Multiple fork-related tactical issues"
    if _all_event_types_start_with(group, "hanging_piece_"):
        return f"Move {move_number}: Multiple piece safety issues"
    if _all_event_types_start_with(group, "knight_outpost_"):
        return f"Move {move_number}: Multiple knight outpost opportunities"

    if group.category == "tactics":
        return f"Move {move_number}: Major tactical issue"

    category_title = group.category.replace("_", " ").title()
    return f"Move {move_number}: Major {category_title.lower()} issue"


def _explanation(group: VerifiedEventGroup) -> str:
    if len(group.events) > 1:
        topic = _group_topic(group)
        return (
            f"Several {topic} were found in this position. "
            f"The largest engine impact was {group.impact_magnitude} centipawns."
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


def _move_number(group: VerifiedEventGroup) -> int:
    return (group.events[0].event.metadata.ply + 1) // 2


def _all_event_types_start_with(group: VerifiedEventGroup, prefix: str) -> bool:
    return all(event.event.event_type.startswith(prefix) for event in group.events)


def _group_topic(group: VerifiedEventGroup) -> str:
    if _all_event_types_start_with(group, "fork_"):
        return "fork-related tactical issues"
    if _all_event_types_start_with(group, "hanging_piece_"):
        return "piece safety issues"
    if _all_event_types_start_with(group, "knight_outpost_"):
        return "knight outpost opportunities"
    if group.category == "tactics":
        return "tactical issues"

    return f"{group.category.replace('_', ' ')} issues"
