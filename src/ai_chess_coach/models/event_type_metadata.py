"""Central metadata registry for detected event types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EventPolarity = Literal["positive", "negative", "neutral"]
VerificationKind = Literal["actual_move", "missed_candidate", "allowed_response"]


@dataclass(frozen=True)
class EventTypeMetadata:
    """Metadata describing how downstream layers should interpret an event type."""

    event_type: str
    display_name: str
    category: str
    polarity: EventPolarity
    verification_kind: VerificationKind = "actual_move"


_EVENT_TYPE_METADATA = {
    metadata.event_type: metadata
    for metadata in (
        EventTypeMetadata(
            event_type="hanging_piece_created",
            display_name="Hanging Piece Created",
            category="piece_safety",
            polarity="negative",
        ),
        EventTypeMetadata(
            event_type="hanging_piece_ignored",
            display_name="Hanging Piece Ignored",
            category="piece_safety",
            polarity="negative",
        ),
        EventTypeMetadata(
            event_type="hanging_piece_lost",
            display_name="Hanging Piece Lost",
            category="piece_safety",
            polarity="negative",
        ),
        EventTypeMetadata(
            event_type="fork_created",
            display_name="Fork Created",
            category="tactics",
            polarity="positive",
        ),
        EventTypeMetadata(
            event_type="fork_missed",
            display_name="Fork Missed",
            category="tactics",
            polarity="negative",
            verification_kind="missed_candidate",
        ),
        EventTypeMetadata(
            event_type="fork_allowed",
            display_name="Fork Allowed",
            category="tactics",
            polarity="negative",
            verification_kind="allowed_response",
        ),
        EventTypeMetadata(
            event_type="knight_outpost_created",
            display_name="Knight Outpost Created",
            category="positional",
            polarity="positive",
        ),
        EventTypeMetadata(
            event_type="knight_outpost_missed",
            display_name="Knight Outpost Missed",
            category="positional",
            polarity="negative",
            verification_kind="missed_candidate",
        ),
    )
}


def get_event_type_metadata(event_type: str) -> EventTypeMetadata:
    """Return metadata for an event type, defaulting unknown types to neutral."""

    return _EVENT_TYPE_METADATA.get(
        event_type,
        EventTypeMetadata(
            event_type=event_type,
            display_name=event_type.replace("_", " ").title(),
            category="unknown",
            polarity="neutral",
        ),
    )


def registered_event_type_metadata() -> tuple[EventTypeMetadata, ...]:
    """Return registered event type metadata in deterministic order."""

    return tuple(
        _EVENT_TYPE_METADATA[event_type]
        for event_type in sorted(_EVENT_TYPE_METADATA)
    )
