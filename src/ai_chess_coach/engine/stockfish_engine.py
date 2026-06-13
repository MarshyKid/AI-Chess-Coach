"""Stockfish wrapper for engine-layer analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from os import PathLike
import shutil
from types import TracebackType

import chess
import chess.engine


@dataclass(frozen=True)
class StockfishAnalysis:
    """Engine-layer result for a single FEN analysis."""

    fen: str
    score: chess.engine.PovScore | None
    best_move: chess.Move | None
    principal_variation: tuple[chess.Move, ...]
    depth: int | None


class StockfishUnavailableError(RuntimeError):
    """Raised when Stockfish cannot be located or started."""


class StockfishEngine:
    """Small deterministic wrapper around a Stockfish UCI process."""

    def __init__(
        self,
        engine_path: str | PathLike[str] | None = None,
        *,
        depth: int = 12,
        engine_options: Mapping[str, object] | None = None,
    ) -> None:
        self.depth = depth
        self.engine_path = _resolve_engine_path(engine_path)
        self._engine: chess.engine.SimpleEngine | None = None

        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        except Exception as exc:
            raise StockfishUnavailableError(
                f"Could not start Stockfish at {self.engine_path!r}."
            ) from exc

        if engine_options:
            try:
                self._engine.configure(dict(engine_options))
            except Exception:
                self.close()
                raise

    def evaluate_fen(self, fen: str, *, depth: int | None = None) -> StockfishAnalysis:
        """Evaluate a FEN and return structured engine-layer analysis."""

        board = chess.Board(fen)
        analysis = self._require_engine().analyse(
            board,
            chess.engine.Limit(depth=depth if depth is not None else self.depth),
        )
        principal_variation = tuple(analysis.get("pv", ()))

        return StockfishAnalysis(
            fen=board.fen(),
            score=analysis.get("score"),
            best_move=principal_variation[0] if principal_variation else None,
            principal_variation=principal_variation,
            depth=analysis.get("depth"),
        )

    def best_move(self, fen: str, *, depth: int | None = None) -> chess.Move | None:
        """Return Stockfish's best move for a FEN."""

        board = chess.Board(fen)
        result = self._require_engine().play(
            board,
            chess.engine.Limit(depth=depth if depth is not None else self.depth),
        )
        return result.move

    def principal_variation(
        self,
        fen: str,
        *,
        depth: int | None = None,
    ) -> tuple[chess.Move, ...]:
        """Return Stockfish's principal variation for a FEN, if available."""

        return self.evaluate_fen(fen, depth=depth).principal_variation

    def close(self) -> None:
        """Close the underlying engine process once."""

        if self._engine is None:
            return

        engine = self._engine
        self._engine = None
        engine.quit()

    def __enter__(self) -> StockfishEngine:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _require_engine(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            raise RuntimeError("Stockfish engine is closed.")

        return self._engine


def _resolve_engine_path(engine_path: str | PathLike[str] | None) -> str:
    if engine_path is not None:
        return os.fspath(engine_path)

    environment_path = os.environ.get("STOCKFISH_PATH")
    if environment_path:
        return environment_path

    discovered_path = shutil.which("stockfish")
    if discovered_path:
        return discovered_path

    raise StockfishUnavailableError(
        "Stockfish executable not found. Pass engine_path or set STOCKFISH_PATH."
    )
