"""Generate deterministic coaching moments from verified events."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import CoachingMoment, VerifiedEvent


class ReviewGenerator:
    """Formats verified events as simple coaching moments."""

    def generate(self, events: Iterable[VerifiedEvent]) -> tuple[CoachingMoment, ...]:
        verified_events = _validated_events(events)

        return tuple(
            _coaching_moment(event)
            for event in sorted(verified_events, key=_sort_key)
        )


def _validated_events(events: Iterable[VerifiedEvent]) -> list[VerifiedEvent]:
    verified_events: list[VerifiedEvent] = []

    for event in events:
        if not isinstance(event, VerifiedEvent):
            raise TypeError("ReviewGenerator.generate() accepts only VerifiedEvent objects.")

        verified_events.append(event)

    return verified_events


def _sort_key(event: VerifiedEvent) -> tuple[float, str, str]:
    return (
        -_review_score(event),
        event.event.event_type,
        event.event.move.uci(),
    )


def _review_score(event: VerifiedEvent) -> float:
    impact_magnitude = event.engine_assessment.impact_magnitude
    if impact_magnitude is not None:
        return float(impact_magnitude)

    eval_delta = event.engine_assessment.eval_delta
    if eval_delta is not None:
        return float(abs(eval_delta))

    return float(event.event.severity)


def _coaching_moment(event: VerifiedEvent) -> CoachingMoment:
    return CoachingMoment(
        title=_title(event.event.event_type),
        explanation=_explanation(event),
        supporting_evidence=(event,),
        position_reference=_position_reference(event),
        highlights=event.event.squares,
    )


def _title(event_type: str) -> str:
    return event_type.replace("_", " ").title()


def _explanation(event: VerifiedEvent) -> str:
    event_title = _title(event.event.event_type)
    eval_delta = event.engine_assessment.eval_delta
    if eval_delta is not None:
        return f"{event_title} was verified with an engine evaluation change of {eval_delta} centipawns."

    return f"{event_title} was detected with detector severity {event.event.severity}."


def _position_reference(event: VerifiedEvent) -> str:
    return event.event.metadata.after_fen
