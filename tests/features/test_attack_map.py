import unittest

import chess

from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import AttackerInfo


class AttackMapTest(unittest.TestCase):
    def test_starting_position_includes_occupied_squares_with_no_attackers(self) -> None:
        attack_map = FeatureStore(chess.Board()).attack_map()

        self.assertIn(chess.E1, attack_map)
        self.assertEqual(attack_map[chess.E1], ())
        self.assertEqual(len(attack_map), 32)

    def test_simple_attacked_piece_maps_to_correct_attacker(self) -> None:
        board = chess.Board("4k3/8/8/8/8/3p4/8/3RK3 b - - 0 1")
        attack_map = FeatureStore(board).attack_map()

        self.assertEqual(
            attack_map[chess.D3],
            (
                AttackerInfo(
                    square=chess.D1,
                    piece=chess.Piece(chess.ROOK, chess.WHITE),
                    is_pinned=False,
                ),
            ),
        )

    def test_empty_squares_are_not_included(self) -> None:
        attack_map = FeatureStore(chess.Board()).attack_map()

        self.assertNotIn(chess.E4, attack_map)

    def test_pinned_attacking_piece_is_marked_pinned(self) -> None:
        board = chess.Board("4k3/4n3/8/3P4/8/8/8/K3R3 b - - 0 1")
        attack_map = FeatureStore(board).attack_map()

        self.assertEqual(
            attack_map[chess.D5],
            (
                AttackerInfo(
                    square=chess.E7,
                    piece=chess.Piece(chess.KNIGHT, chess.BLACK),
                    is_pinned=True,
                ),
            ),
        )

    def test_repeated_calls_return_cached_result(self) -> None:
        store = FeatureStore(chess.Board())

        first = store.attack_map()
        second = store.attack_map()

        self.assertIs(first, second)
        self.assertIn("attack_map", store.cached_feature_names())

    def test_external_board_mutation_does_not_affect_attack_map(self) -> None:
        board = chess.Board("4k3/8/8/8/8/3p4/8/3RK3 b - - 0 1")
        store = FeatureStore(board)
        board.clear_board()

        attack_map = store.attack_map()

        self.assertIn(chess.D3, attack_map)
        self.assertEqual(attack_map[chess.D3][0].square, chess.D1)
