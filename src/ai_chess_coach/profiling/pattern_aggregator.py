"""Aggregate verified events into detected patterns."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import DetectedPattern, VerifiedEvent


class PatternAggregator:
    """Groups verified events into recurring event-type patterns."""

    def aggregate(self, events: Iterable[VerifiedEvent]) -> tuple[DetectedPattern, ...]:
        grouped_events: dict[str, list[VerifiedEvent]] = {}

        for event in events:
            if not isinstance(event, VerifiedEvent):
                raise TypeError("PatternAggregator.aggregate() accepts only VerifiedEvent objects.")

            grouped_events.setdefault(event.event.event_type, []).append(event)

        return tuple(
            DetectedPattern(
                pattern_type=pattern_type,
                frequency=len(supporting_events),
                severity=_summarize_severity(supporting_events),
                supporting_events=tuple(supporting_events),
            )
            for pattern_type, supporting_events in sorted(grouped_events.items())
        )


def _summarize_severity(events: list[VerifiedEvent]) -> float:
    eval_deltas = [
        abs(event.engine_assessment.eval_delta)
        for event in events
        if event.engine_assessment.eval_delta is not None
    ]
    if eval_deltas:
        return float(sum(eval_deltas) / len(eval_deltas))

    return float(sum(event.event.severity for event in events) / len(events))
