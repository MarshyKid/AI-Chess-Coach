"""Engine score domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import chess

MATE_RANK_BASE = 10_000_000
ScoreKind = Literal["centipawn", "mate", "unavailable"]


@dataclass(frozen=True)
class EngineScore:
    """A raw engine score from White's perspective."""

    centipawns: int | None = None
    mate: int | None = None

    def __post_init__(self) -> None:
        if self.centipawns is not None and self.mate is not None:
            raise ValueError("EngineScore cannot contain both centipawns and mate.")

    @property
    def kind(self) -> ScoreKind:
        """Return the score representation kind."""

        if self.centipawns is not None:
            return "centipawn"
        if self.mate is not None:
            return "mate"

        return "unavailable"

    def for_side(self, side: chess.Color) -> EngineScore:
        """Return this score from the given side's perspective."""

        if side == chess.WHITE:
            return self
        if self.centipawns is not None:
            return EngineScore(centipawns=-self.centipawns)
        if self.mate is not None:
            return EngineScore(mate=-self.mate)

        return self

    def rank_value(self) -> int | None:
        """Return an internal rank value for ordering scores."""

        if self.centipawns is not None:
            return self.centipawns
        if self.mate is not None:
            if self.mate > 0:
                return MATE_RANK_BASE - abs(self.mate)
            if self.mate < 0:
                return -MATE_RANK_BASE + abs(self.mate)

            return MATE_RANK_BASE

        return None
