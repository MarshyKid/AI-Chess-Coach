import unittest
from unittest.mock import patch

import chess.pgn

from ai_chess_coach.analysis import load_game_from_pgn_string


class PgnLoaderTest(unittest.TestCase):
    def test_loads_valid_pgn_string(self) -> None:
        pgn = """
[Event "Task 2 Test"]
[Site "?"]
[Date "2026.06.13"]
[Round "?"]
[White "White"]
[Black "Black"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""

        game = load_game_from_pgn_string(pgn)

        self.assertIsInstance(game, chess.pgn.Game)
        self.assertEqual(game.headers["Event"], "Task 2 Test")

    def test_preserves_headers_from_pgn(self) -> None:
        pgn = """
[Event "Header Test"]
[White "Ada"]
[Black "Grace"]
[Result "*"]

1. d4 *
"""

        game = load_game_from_pgn_string(pgn)

        self.assertEqual(game.headers["Event"], "Header Test")
        self.assertEqual(game.headers["White"], "Ada")
        self.assertEqual(game.headers["Black"], "Grace")

    def test_raises_for_empty_pgn_text(self) -> None:
        with self.assertRaises(ValueError):
            load_game_from_pgn_string(" \n\t ")

    def test_raises_when_read_game_returns_none(self) -> None:
        with patch("chess.pgn.read_game", return_value=None):
            with self.assertRaises(ValueError):
                load_game_from_pgn_string("not empty")
