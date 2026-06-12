"""Move-level domain model."""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class MoveTransition:
    """Represents one half-move and the board states around it."""

    ply: int
    san: str
    move: chess.Move
    before_position: chess.Board
    after_position: chess.Board
