"""Machine-facing detector output model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class DetectedEvent:
    """Structured occurrence found by a deterministic detector."""

    event_type: str
    side: chess.Color
    move: chess.Move
    position: chess.Board
    squares: tuple[chess.Square, ...]
    evidence: Mapping[str, object]
    severity: float
