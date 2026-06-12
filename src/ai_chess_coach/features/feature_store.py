"""Central feature cache for board analysis."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

import chess

from ai_chess_coach.models import PositionAnalysis

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
