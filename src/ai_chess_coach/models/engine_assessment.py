"""Objective engine evidence domain model."""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class EngineAssessment:
    """Objective engine evidence for a position or detected event."""

    eval_before: int | None
    eval_after: int | None
    eval_delta: int | None
    best_move: chess.Move | None
    principal_variation: tuple[chess.Move, ...]
    depth: int | None
    eval_delta_for_event_side: int | None = None
    impact_magnitude: int | None = None
    candidate_eval_after: int | None = None
    candidate_move_uci: str | None = None
    candidate_after_fen: str | None = None
    event_impact_for_side: int | None = None
