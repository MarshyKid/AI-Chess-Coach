"""Candidate move model for counterfactual event verification."""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class CandidateMove:
    """Typed candidate move evidence used by engine verification."""

    move_uci: str
    move_san: str | None
    start_fen: str
    side: chess.Color
