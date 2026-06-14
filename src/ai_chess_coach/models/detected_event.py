"""Machine-facing detector output model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import chess

from ai_chess_coach.models.event_metadata import EventMetadata


@dataclass(frozen=True)
class DetectedEvent:
    """Structured occurrence found by a deterministic detector.

    The side is the color/player the event is attributed to. It is not
    necessarily the player who made the move.
    """

    event_type: str
    side: chess.Color
    move: chess.Move
    position: chess.Board
    squares: tuple[chess.Square, ...]
    metadata: EventMetadata
    evidence: Mapping[str, object]
    severity: float
