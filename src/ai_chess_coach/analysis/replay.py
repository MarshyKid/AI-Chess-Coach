"""PGN replay utilities."""

from __future__ import annotations

import chess.pgn

from ai_chess_coach.analysis.pgn_loader import load_game_from_pgn_string
from ai_chess_coach.models import MoveTransition


def replay_game(game: chess.pgn.Game) -> list[MoveTransition]:
    """Replay a PGN game mainline into move transitions."""

    board = game.board()
    transitions: list[MoveTransition] = []

    for ply, move in enumerate(game.mainline_moves(), start=1):
        before_position = board.copy(stack=False)
        san = board.san(move)
        board.push(move)
        after_position = board.copy(stack=False)

        transitions.append(
            MoveTransition(
                ply=ply,
                san=san,
                move=move,
                before_position=before_position,
                after_position=after_position,
            )
        )

    return transitions


def replay_pgn_string(pgn_text: str) -> list[MoveTransition]:
    """Load and replay the first game from a PGN string."""

    return replay_game(load_game_from_pgn_string(pgn_text))
