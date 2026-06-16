import unittest
from dataclasses import FrozenInstanceError

import chess

from ai_chess_coach.models import EngineScore, MATE_RANK_BASE


class EngineScoreTest(unittest.TestCase):
    def test_centipawn_score_has_centipawn_kind_and_rank(self) -> None:
        score = EngineScore(centipawns=125)

        self.assertEqual(score.kind, "centipawn")
        self.assertEqual(score.rank_value(), 125)

    def test_positive_mate_score_has_mate_kind_and_rank(self) -> None:
        score = EngineScore(mate=3)

        self.assertEqual(score.kind, "mate")
        self.assertEqual(score.rank_value(), MATE_RANK_BASE - 3)

    def test_negative_mate_score_has_mate_kind_and_rank(self) -> None:
        score = EngineScore(mate=-4)

        self.assertEqual(score.kind, "mate")
        self.assertEqual(score.rank_value(), -MATE_RANK_BASE + 4)

    def test_zero_mate_score_is_ranked_deterministically(self) -> None:
        score = EngineScore(mate=0)

        self.assertEqual(score.kind, "mate")
        self.assertEqual(score.rank_value(), MATE_RANK_BASE)

    def test_unavailable_score_has_no_rank(self) -> None:
        score = EngineScore()

        self.assertEqual(score.kind, "unavailable")
        self.assertIsNone(score.rank_value())

    def test_faster_favorable_mate_ranks_higher(self) -> None:
        self.assertGreater(
            EngineScore(mate=1).rank_value(),
            EngineScore(mate=3).rank_value(),
        )

    def test_faster_unfavorable_mate_ranks_lower(self) -> None:
        self.assertLess(
            EngineScore(mate=-1).rank_value(),
            EngineScore(mate=-3).rank_value(),
        )

    def test_favorable_mate_outranks_centipawns(self) -> None:
        self.assertGreater(
            EngineScore(mate=10).rank_value(),
            EngineScore(centipawns=900_000).rank_value(),
        )

    def test_unfavorable_mate_ranks_below_centipawns(self) -> None:
        self.assertLess(
            EngineScore(mate=-10).rank_value(),
            EngineScore(centipawns=-900_000).rank_value(),
        )

    def test_for_side_flips_black_perspective(self) -> None:
        self.assertEqual(
            EngineScore(centipawns=120).for_side(chess.BLACK),
            EngineScore(centipawns=-120),
        )
        self.assertEqual(
            EngineScore(mate=2).for_side(chess.BLACK),
            EngineScore(mate=-2),
        )

    def test_for_side_keeps_white_perspective(self) -> None:
        score = EngineScore(mate=2)

        self.assertIs(score.for_side(chess.WHITE), score)

    def test_cannot_set_centipawns_and_mate_together(self) -> None:
        with self.assertRaises(ValueError):
            EngineScore(centipawns=10, mate=2)

    def test_model_is_frozen(self) -> None:
        score = EngineScore(centipawns=10)

        with self.assertRaises(FrozenInstanceError):
            score.centipawns = 20  # type: ignore[misc]

    def test_engine_score_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.EngineScore, EngineScore)
        self.assertEqual(models.MATE_RANK_BASE, MATE_RANK_BASE)
