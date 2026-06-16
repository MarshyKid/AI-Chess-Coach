"""Objective engine evidence domain model."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from ai_chess_coach.models.engine_score import EngineScore, ScoreKind


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
    score_before: EngineScore | None = None
    score_after: EngineScore | None = None
    candidate_score_after: EngineScore | None = None
    event_score_kind: ScoreKind = "unavailable"
    event_impact_rank_for_side: int | None = None
    impact_rank: int | None = None
