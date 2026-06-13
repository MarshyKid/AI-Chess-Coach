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
