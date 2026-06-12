"""PGN loading utilities."""

from __future__ import annotations

import io

import chess.pgn


def load_game_from_pgn_string(pgn_text: str) -> chess.pgn.Game:
    """Load the first game from a PGN string."""

    if not pgn_text.strip():
        raise ValueError("PGN text must not be empty.")

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("No PGN game could be parsed.")

    return game
