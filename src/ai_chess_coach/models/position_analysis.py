"""Position snapshot domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chess


@dataclass(frozen=True)
class PositionAnalysis:
    """Represents a board snapshot prepared for later feature analysis."""

    board: chess.Board
    fen: str
    feature_store: Any | None = None
