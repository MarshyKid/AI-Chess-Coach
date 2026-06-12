import unittest

import chess

from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import DefenderInfo


class DefenderMapTest(unittest.TestCase):
    def test_starting_position_includes_occupied_squares_with_no_defenders(self) -> None:
        defender_map = FeatureStore(chess.Board()).defender_map()

        self.assertIn(chess.A1, defender_map)
        self.assertEqual(defender_map[chess.A1], ())
        self.assertEqual(len(defender_map), 32)

    def test_simple_defended_piece_maps_to_correct_defender(self) -> None:
        board = chess.Board("4k3/8/8/8/8/3P4/8/3RK3 w - - 0 1")
        defender_map = FeatureStore(board).defender_map()

        self.assertEqual(
            defender_map[chess.D3],
            (
                DefenderInfo(
                    square=chess.D1,
                    piece=chess.Piece(chess.ROOK, chess.WHITE),
                    is_pinned=False,
                    is_overloaded=False,
                ),
            ),
        )

    def test_empty_squares_are_not_included(self) -> None:
        defender_map = FeatureStore(chess.Board()).defender_map()

        self.assertNotIn(chess.E4, defender_map)

    def test_pinned_defending_piece_is_marked_pinned(self) -> None:
        board = chess.Board("4r2k/8/8/8/3P4/8/4N3/4K3 w - - 0 1")
        defender_map = FeatureStore(board).defender_map()

        self.assertEqual(
            defender_map[chess.D4],
            (
                DefenderInfo(
                    square=chess.E2,
                    piece=chess.Piece(chess.KNIGHT, chess.WHITE),
                    is_pinned=True,
                    is_overloaded=False,
                ),
            ),
        )

    def test_is_overloaded_is_false_by_default_for_all_defenders(self) -> None:
        board = chess.Board("4k3/8/8/8/8/3P4/8/3RK3 w - - 0 1")
        defender_map = FeatureStore(board).defender_map()

        self.assertTrue(
            all(
                not defender.is_overloaded
                for defenders in defender_map.values()
                for defender in defenders
            )
        )

    def test_repeated_calls_return_cached_result(self) -> None:
        store = FeatureStore(chess.Board())

        first = store.defender_map()
        second = store.defender_map()

        self.assertIs(first, second)
        self.assertIn("defender_map", store.cached_feature_names())

    def test_external_board_mutation_does_not_affect_defender_map(self) -> None:
        board = chess.Board("4k3/8/8/8/8/3P4/8/3RK3 w - - 0 1")
        store = FeatureStore(board)
        board.clear_board()

        defender_map = store.defender_map()

        self.assertIn(chess.D3, defender_map)
        self.assertEqual(defender_map[chess.D3][0].square, chess.D1)
