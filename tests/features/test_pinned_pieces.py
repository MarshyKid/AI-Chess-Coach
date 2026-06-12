import unittest

import chess

from ai_chess_coach.features import FeatureStore


class PinnedPiecesTest(unittest.TestCase):
    def test_starting_position_has_no_pinned_pieces(self) -> None:
        store = FeatureStore(chess.Board())

        self.assertEqual(store.pinned_pieces(), ())

    def test_detects_white_piece_absolutely_pinned_to_white_king(self) -> None:
        board = chess.Board("k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1")
        store = FeatureStore(board)

        self.assertEqual(store.pinned_pieces(), (chess.E2,))

    def test_detects_black_piece_absolutely_pinned_to_black_king(self) -> None:
        board = chess.Board("4k3/4n3/8/8/8/8/8/K3R3 b - - 0 1")
        store = FeatureStore(board)

        self.assertEqual(store.pinned_pieces(), (chess.E7,))

    def test_repeated_calls_return_cached_result(self) -> None:
        board = chess.Board("k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1")
        store = FeatureStore(board)

        first = store.pinned_pieces()
        second = store.pinned_pieces()

        self.assertIs(first, second)
        self.assertIn("pinned_pieces", store.cached_feature_names())

    def test_external_board_mutation_does_not_affect_pinned_pieces(self) -> None:
        board = chess.Board()
        store = FeatureStore(board)
        board.set_fen("k3r3/8/8/8/8/8/4N3/4K3 w - - 0 1")

        self.assertEqual(store.pinned_pieces(), ())
