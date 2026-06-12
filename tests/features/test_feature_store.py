import unittest

import chess

from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import PositionAnalysis


class FeatureStoreTest(unittest.TestCase):
    def test_accepts_chess_board(self) -> None:
        board = chess.Board()

        store = FeatureStore(board)

        self.assertEqual(store.fen, board.fen())

    def test_accepts_position_analysis(self) -> None:
        board = chess.Board()
        position = PositionAnalysis(board=board, fen=board.fen())

        store = FeatureStore(position)

        self.assertEqual(store.fen, board.fen())

    def test_snapshots_original_board(self) -> None:
        board = chess.Board()
        store = FeatureStore(board)

        board.push(chess.Move.from_uci("e2e4"))

        self.assertEqual(store.fen, chess.Board().fen())

    def test_board_property_returns_defensive_copy(self) -> None:
        store = FeatureStore(chess.Board())
        returned_board = store.board

        returned_board.push(chess.Move.from_uci("e2e4"))

        self.assertEqual(store.fen, chess.Board().fen())

    def test_compute_is_lazy_until_feature_is_requested(self) -> None:
        store = FeatureStore(chess.Board())
        calls = 0

        def compute() -> str:
            nonlocal calls
            calls += 1
            return "computed"

        self.assertEqual(calls, 0)

        result = store.get_or_compute("example", compute)

        self.assertEqual(result, "computed")
        self.assertEqual(calls, 1)

    def test_repeated_access_returns_cached_value_without_recomputing(self) -> None:
        store = FeatureStore(chess.Board())
        calls = 0
        value = object()

        def compute() -> object:
            nonlocal calls
            calls += 1
            return value

        first = store.get_or_compute("example", compute)
        second = store.get_or_compute("example", compute)

        self.assertIs(first, value)
        self.assertIs(second, value)
        self.assertEqual(calls, 1)

    def test_different_feature_names_are_cached_independently(self) -> None:
        store = FeatureStore(chess.Board())
        calls: list[str] = []

        first = store.get_or_compute("first", lambda: calls.append("first") or "a")
        second = store.get_or_compute("second", lambda: calls.append("second") or "b")

        self.assertEqual(first, "a")
        self.assertEqual(second, "b")
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(store.cached_feature_names(), ("first", "second"))

    def test_clear_cache_allows_recomputation(self) -> None:
        store = FeatureStore(chess.Board())
        calls = 0

        def compute() -> int:
            nonlocal calls
            calls += 1
            return calls

        self.assertEqual(store.get_or_compute("example", compute), 1)
        store.clear_cache()
        self.assertEqual(store.cached_feature_names(), ())
        self.assertEqual(store.get_or_compute("example", compute), 2)
        self.assertEqual(calls, 2)

    def test_cached_feature_names_returns_currently_cached_names(self) -> None:
        store = FeatureStore(chess.Board())

        self.assertEqual(store.cached_feature_names(), ())

        store.get_or_compute("alpha", lambda: object())
        store.get_or_compute("beta", lambda: object())

        self.assertEqual(store.cached_feature_names(), ("alpha", "beta"))
