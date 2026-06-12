import unittest

import chess

from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import PieceSafety


class PieceSafetyFeatureTest(unittest.TestCase):
    def test_starting_position_returns_piece_safety_for_occupied_squares(self) -> None:
        piece_safety = FeatureStore(chess.Board()).piece_safety()

        self.assertEqual(len(piece_safety), 32)
        self.assertTrue(all(isinstance(safety, PieceSafety) for safety in piece_safety.values()))

    def test_empty_squares_are_not_included(self) -> None:
        piece_safety = FeatureStore(chess.Board()).piece_safety()

        self.assertNotIn(chess.E4, piece_safety)

    def test_loose_piece_has_no_defenders(self) -> None:
        board = chess.Board("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1")
        safety = FeatureStore(board).piece_safety()[chess.D4]

        self.assertEqual(safety.defenders, ())
        self.assertTrue(safety.is_loose)

    def test_attacked_undefended_piece_is_hanging(self) -> None:
        board = chess.Board("3r3k/8/8/8/3B4/8/8/4K3 w - - 0 1")
        safety = FeatureStore(board).piece_safety()[chess.D4]

        self.assertEqual(len(safety.attackers), 1)
        self.assertEqual(safety.defenders, ())
        self.assertTrue(safety.is_hanging)

    def test_defended_attacked_piece_is_not_hanging(self) -> None:
        board = chess.Board("3r3k/8/8/8/3B4/8/8/3RK3 w - - 0 1")
        safety = FeatureStore(board).piece_safety()[chess.D4]

        self.assertEqual(len(safety.attackers), 1)
        self.assertEqual(len(safety.defenders), 1)
        self.assertFalse(safety.is_hanging)

    def test_pinned_piece_is_marked_pinned(self) -> None:
        board = chess.Board("k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1")
        safety = FeatureStore(board).piece_safety()[chess.E2]

        self.assertTrue(safety.is_pinned)

    def test_attackers_and_defenders_come_from_existing_maps(self) -> None:
        board = chess.Board("3r3k/8/8/8/3B4/8/8/3RK3 w - - 0 1")
        store = FeatureStore(board)

        piece_safety = store.piece_safety()
        attack_map = store.attack_map()
        defender_map = store.defender_map()

        self.assertEqual(piece_safety[chess.D4].attackers, attack_map[chess.D4])
        self.assertEqual(piece_safety[chess.D4].defenders, defender_map[chess.D4])

    def test_see_value_is_none_for_now(self) -> None:
        piece_safety = FeatureStore(chess.Board()).piece_safety()

        self.assertTrue(all(safety.see_value is None for safety in piece_safety.values()))

    def test_repeated_calls_return_cached_result(self) -> None:
        store = FeatureStore(chess.Board())

        first = store.piece_safety()
        second = store.piece_safety()

        self.assertIs(first, second)
        self.assertIn("piece_safety", store.cached_feature_names())

    def test_external_board_mutation_does_not_affect_piece_safety(self) -> None:
        board = chess.Board("3r3k/8/8/8/3B4/8/8/4K3 w - - 0 1")
        store = FeatureStore(board)
        board.clear_board()

        piece_safety = store.piece_safety()

        self.assertIn(chess.D4, piece_safety)
        self.assertEqual(piece_safety[chess.D4].piece, chess.Piece(chess.BISHOP, chess.WHITE))
        self.assertEqual(piece_safety[chess.D4].attackers[0].square, chess.D8)
