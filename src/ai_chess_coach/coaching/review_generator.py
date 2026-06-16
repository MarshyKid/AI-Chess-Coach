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
    event_type = group.events[0].event.event_type
    metadata = get_event_type_metadata(event_type)
    if event_type.startswith("fork_"):
        return f"Move {move_number}: {metadata.display_name}"
    if event_type.startswith("hanging_piece_"):
        return f"Move {move_number}: Piece safety issue"
    if event_type.startswith("knight_outpost_"):
        return f"Move {move_number}: Knight outpost opportunity"

    return f"Move {move_number}: {metadata.display_name}"


def _explanation(group: VerifiedEventGroup) -> str:
    event = group.events[0]
    event_title = event.event.event_type.replace("_", " ").title()
    event_impact = event.engine_assessment.event_impact_for_side
    impact_magnitude = event.engine_assessment.impact_magnitude
    if event.engine_assessment.event_score_kind == "mate":
        return _mate_explanation(event)

    verification_kind = get_event_type_metadata(event.event.event_type).verification_kind
    if event_impact is None or impact_magnitude is None:
        return f"{event_title} was detected with detector severity {event.event.severity}."

    if verification_kind == "missed_candidate":
        if event_impact < 0:
            return f"The candidate move was about {impact_magnitude} centipawns better than the move played."

        return f"The candidate move was about {impact_magnitude} centipawns worse than the move played."

    if verification_kind == "allowed_response":
        if event_impact < 0:
            return f"After this move, the opponent had a reply worth about {impact_magnitude} centipawns."

        return f"The opponent reply did not improve over the played position by about {impact_magnitude} centipawns."

    if event_impact < 0:
        return f"This move was harmful for the event side by about {impact_magnitude} centipawns."

    if event_impact > 0:
        return f"This move helped the event side by about {impact_magnitude} centipawns."

    return f"{event_title} was detected with detector severity {event.event.severity}."


def _mate_explanation(event: VerifiedEvent) -> str:
    event_impact = event.engine_assessment.event_impact_rank_for_side
    verification_kind = get_event_type_metadata(event.event.event_type).verification_kind
    if event_impact is None:
        event_title = event.event.event_type.replace("_", " ").title()
        return f"{event_title} was detected with detector severity {event.event.severity}."

    if verification_kind == "missed_candidate":
        candidate_score = event.engine_assessment.candidate_score_after
        if candidate_score is not None and candidate_score.kind == "mate":
            outcome = _mate_outcome(candidate_score, event.event.side)
            if event_impact < 0:
                return f"The candidate move led to {outcome}, which was better than the move played."

            return f"The candidate move led to {outcome}, but was worse than the move played."
        if event_impact < 0:
            return "The candidate move produced a better mate-aware outcome than the move played."

        return "The candidate move produced a worse mate-aware outcome than the move played."

    if verification_kind == "allowed_response":
        candidate_score = event.engine_assessment.candidate_score_after
        if candidate_score is not None and candidate_score.kind == "mate":
            outcome = _mate_outcome(candidate_score, event.event.side)
            if event_impact < 0:
                return f"After this move, the opponent had a reply leading to {outcome}."

            return f"The opponent reply led to {outcome}, but did not improve over the played position."
        if event_impact < 0:
            return "After this move, the opponent had a mate-aware reply."

        return "The opponent reply did not improve over the played position in mate-aware terms."

    after_score = event.engine_assessment.score_after
    if after_score is not None and after_score.kind == "mate":
        outcome = _mate_outcome(after_score, event.event.side)
        if event_impact < 0:
            return f"This move led to {outcome}."

        return f"This move led to {outcome}."

    if event_impact < 0:
        return "This move worsened the event side's position in mate-aware terms."

    return "This move improved the event side's position in mate-aware terms."


def _mate_outcome(score, side: chess.Color) -> str:
    side_score = score.for_side(side)
    if side_score.mate is None:
        return "a mate-aware outcome"
    if side_score.mate > 0:
        return f"a forced mate for the event side in {side_score.mate}"
    if side_score.mate < 0:
        return f"a forced mate against the event side in {abs(side_score.mate)}"

    return "a forced mate for the event side"


def _position_reference(group: VerifiedEventGroup) -> str:
    event = group.events[0].event
    verification_kind = get_event_type_metadata(event.event_type).verification_kind
    if verification_kind == "missed_candidate":
        return event.metadata.before_fen

    return event.metadata.after_fen


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
