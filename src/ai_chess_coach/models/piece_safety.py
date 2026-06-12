"""Piece-safety domain models."""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass(frozen=True)
class AttackerInfo:
    """Structured information about a piece attacking a target."""

    square: chess.Square
    piece: chess.Piece
    is_pinned: bool


@dataclass(frozen=True)
class DefenderInfo:
    """Structured information about a piece defending a target."""

    square: chess.Square
    piece: chess.Piece
    is_pinned: bool
    is_overloaded: bool


@dataclass(frozen=True)
class PieceSafety:
    """Tactical safety facts for one occupied square."""

    square: chess.Square
    piece: chess.Piece
    attackers: tuple[AttackerInfo, ...]
    defenders: tuple[DefenderInfo, ...]
    is_pinned: bool
    see_value: int | None = None

    @property
    def is_loose(self) -> bool:
        """Whether the piece has no defenders at all."""

        return len(self.defenders) == 0

    @property
    def is_hanging(self) -> bool:
        """Whether the piece is attacked and has no reliable defense."""

        return bool(self._effective_attackers) and not self._reliable_defenders

    @property
    def is_under_defended(self) -> bool:
        """Whether effective attackers outnumber reliable defenders."""

        return len(self._effective_attackers) > len(self._reliable_defenders)

    @property
    def is_outnumbered(self) -> bool:
        """Whether effective attackers outnumber all listed defenders."""

        return len(self._effective_attackers) > len(self.defenders)

    @property
    def _effective_attackers(self) -> tuple[AttackerInfo, ...]:
        return tuple(attacker for attacker in self.attackers if not attacker.is_pinned)

    @property
    def _reliable_defenders(self) -> tuple[DefenderInfo, ...]:
        return tuple(
            defender
            for defender in self.defenders
            if not defender.is_pinned and not defender.is_overloaded
        )
