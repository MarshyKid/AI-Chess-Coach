import unittest

import chess

from ai_chess_coach.analysis import replay_game, replay_pgn_string
from ai_chess_coach.analysis.pgn_loader import load_game_from_pgn_string
from ai_chess_coach.models import MoveTransition


class ReplayTest(unittest.TestCase):
    def test_replays_one_transition_per_mainline_move(self) -> None:
        pgn = """
[Event "Replay Test"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 *
"""

        transitions = replay_pgn_string(pgn)

        self.assertEqual(len(transitions), 4)
        self.assertTrue(all(isinstance(transition, MoveTransition) for transition in transitions))

    def test_ply_starts_at_one_and_increments_by_half_move(self) -> None:
        transitions = replay_pgn_string("""
[Event "Ply Test"]
[Result "*"]

1. e4 e5 2. Nf3 *
""")

        self.assertEqual([transition.ply for transition in transitions], [1, 2, 3])

    def test_san_is_captured_before_each_move_is_pushed(self) -> None:
        transitions = replay_pgn_string("""
[Event "SAN Test"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
""")

        self.assertEqual([transition.san for transition in transitions], ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"])

    def test_before_and_after_positions_are_correct(self) -> None:
        transitions = replay_pgn_string("""
[Event "Position Test"]
[Result "*"]

1. e4 *
""")

        transition = transitions[0]

        self.assertEqual(transition.before_position.fen(), chess.Board().fen())
        self.assertIsNone(transition.before_position.piece_at(chess.E4))
        self.assertEqual(transition.after_position.piece_at(chess.E4), chess.Piece(chess.PAWN, chess.WHITE))
        self.assertIsNone(transition.after_position.piece_at(chess.E2))

    def test_stored_positions_are_independent_snapshots(self) -> None:
        transitions = replay_pgn_string("""
[Event "Snapshot Test"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 *
""")

        first_after_fen = transitions[0].after_position.fen()
        final_after_fen = transitions[-1].after_position.fen()

        self.assertNotEqual(first_after_fen, final_after_fen)
        self.assertEqual(transitions[0].after_position.piece_at(chess.E4), chess.Piece(chess.PAWN, chess.WHITE))
        self.assertIsNone(transitions[0].after_position.piece_at(chess.E5))

    def test_replay_game_accepts_loaded_game(self) -> None:
        pgn = """
[Event "Composition Test"]
[Result "*"]

1. d4 d5 *
"""
        game = load_game_from_pgn_string(pgn)

        transitions = replay_game(game)

        self.assertEqual([transition.san for transition in transitions], ["d4", "d5"])

    def test_replay_respects_setup_and_fen_headers(self) -> None:
        pgn = """
[Event "FEN Test"]
[SetUp "1"]
[FEN "7k/8/8/8/8/8/4K3/R7 w - - 0 1"]
[Result "*"]

1. Ra8+ *
"""

        transitions = replay_pgn_string(pgn)

        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0].before_position.fen(), "7k/8/8/8/8/8/4K3/R7 w - - 0 1")
        self.assertEqual(transitions[0].san, "Ra8+")
