"""Central feature cache for board analysis."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

import chess

from ai_chess_coach.models import AttackerInfo, DefenderInfo, PositionAnalysis

T = TypeVar("T")


class FeatureStore:
    """Provides lazy, cached access to reusable board features."""

    def __init__(self, source: chess.Board | PositionAnalysis) -> None:
        if isinstance(source, PositionAnalysis):
            source_board = source.board
        else:
            source_board = source

        self._board = source_board.copy(stack=False)
        self._cache: dict[str, object] = {}

    @property
    def board(self) -> chess.Board:
        """Return a defensive copy of the stored board snapshot."""

        return self._board.copy(stack=False)

    @property
    def fen(self) -> str:
        """Return the FEN for the stored board snapshot."""

        return self._board.fen()

    def pinned_pieces(self) -> tuple[chess.Square, ...]:
        """Return occupied squares containing pieces pinned to their king."""

        return self.get_or_compute("pinned_pieces", self._compute_pinned_pieces)

    def attack_map(self) -> dict[chess.Square, tuple[AttackerInfo, ...]]:
        """Return opponent attackers for every occupied square."""

        return self.get_or_compute("attack_map", self._compute_attack_map)

    def defender_map(self) -> dict[chess.Square, tuple[DefenderInfo, ...]]:
        """Return same-color defenders for every occupied square."""

        return self.get_or_compute("defender_map", self._compute_defender_map)

    def get_or_compute(self, feature_name: str, compute: Callable[[], T]) -> T:
        """Return a cached feature value, computing it on first access."""

        if feature_name not in self._cache:
            self._cache[feature_name] = compute()

        return cast(T, self._cache[feature_name])

    def clear_cache(self) -> None:
        """Clear all cached feature values."""

        self._cache.clear()

    def cached_feature_names(self) -> tuple[str, ...]:
        """Return the names of currently cached features."""

        return tuple(self._cache)

    def _compute_pinned_pieces(self) -> tuple[chess.Square, ...]:
        pinned_squares: list[chess.Square] = []

        for square in chess.SQUARES:
            piece = self._board.piece_at(square)
            if piece is None:
                continue
            if self._board.is_pinned(piece.color, square):
                pinned_squares.append(square)

        return tuple(pinned_squares)

    def _compute_attack_map(self) -> dict[chess.Square, tuple[AttackerInfo, ...]]:
        attack_map: dict[chess.Square, tuple[AttackerInfo, ...]] = {}

        for target_square in chess.SQUARES:
            target_piece = self._board.piece_at(target_square)
            if target_piece is None:
                continue

            attacker_squares = self._board.attackers(not target_piece.color, target_square)
            attackers: list[AttackerInfo] = []
            for attacker_square in sorted(attacker_squares):
                attacker_piece = self._board.piece_at(attacker_square)
                if attacker_piece is None:
                    continue

                attackers.append(
                    AttackerInfo(
                        square=attacker_square,
                        piece=attacker_piece,
                        is_pinned=self._board.is_pinned(attacker_piece.color, attacker_square),
                    )
                )

            attack_map[target_square] = tuple(attackers)

        return attack_map

    def _compute_defender_map(self) -> dict[chess.Square, tuple[DefenderInfo, ...]]:
        defender_map: dict[chess.Square, tuple[DefenderInfo, ...]] = {}

        for target_square in chess.SQUARES:
            target_piece = self._board.piece_at(target_square)
            if target_piece is None:
                continue

            defender_squares = self._board.attackers(target_piece.color, target_square)
            defenders: list[DefenderInfo] = []
            for defender_square in sorted(defender_squares):
                defender_piece = self._board.piece_at(defender_square)
                if defender_piece is None:
                    continue

                defenders.append(
                    DefenderInfo(
                        square=defender_square,
                        piece=defender_piece,
                        is_pinned=self._board.is_pinned(defender_piece.color, defender_square),
                        is_overloaded=False,
                    )
                )

            defender_map[target_square] = tuple(defenders)

        return defender_map
