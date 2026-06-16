import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import chess

from ai_chess_coach.models import EngineAssessment, EngineScore


class EngineAssessmentTest(unittest.TestCase):
    def test_can_be_constructed_with_all_fields(self) -> None:
        best_move = chess.Move.from_uci("e2e4")
        principal_variation = (
            best_move,
            chess.Move.from_uci("e7e5"),
        )

        assessment = EngineAssessment(
            eval_before=25,
            eval_after=80,
            eval_delta=55,
            best_move=best_move,
            principal_variation=principal_variation,
            depth=14,
            eval_delta_for_event_side=55,
            impact_magnitude=55,
            candidate_eval_after=120,
            candidate_move_uci="d2d4",
            candidate_after_fen="candidate-after-fen",
            event_impact_for_side=-40,
            score_before=EngineScore(centipawns=25),
            score_after=EngineScore(centipawns=80),
            candidate_score_after=EngineScore(centipawns=120),
            event_score_kind="centipawn",
            event_impact_rank_for_side=-40,
            impact_rank=40,
        )

        self.assertEqual(assessment.eval_before, 25)
        self.assertEqual(assessment.eval_after, 80)
        self.assertEqual(assessment.eval_delta, 55)
        self.assertEqual(assessment.best_move, best_move)
        self.assertEqual(assessment.principal_variation, principal_variation)
        self.assertEqual(assessment.depth, 14)
        self.assertEqual(assessment.eval_delta_for_event_side, 55)
        self.assertEqual(assessment.impact_magnitude, 55)
        self.assertEqual(assessment.candidate_eval_after, 120)
        self.assertEqual(assessment.candidate_move_uci, "d2d4")
        self.assertEqual(assessment.candidate_after_fen, "candidate-after-fen")
        self.assertEqual(assessment.event_impact_for_side, -40)
        self.assertEqual(assessment.score_before, EngineScore(centipawns=25))
        self.assertEqual(assessment.score_after, EngineScore(centipawns=80))
        self.assertEqual(assessment.candidate_score_after, EngineScore(centipawns=120))
        self.assertEqual(assessment.event_score_kind, "centipawn")
        self.assertEqual(assessment.event_impact_rank_for_side, -40)
        self.assertEqual(assessment.impact_rank, 40)

    def test_supports_missing_evals_best_move_and_depth(self) -> None:
        assessment = EngineAssessment(
            eval_before=None,
            eval_after=None,
            eval_delta=None,
            best_move=None,
            principal_variation=(),
            depth=None,
        )

        self.assertIsNone(assessment.eval_before)
        self.assertIsNone(assessment.eval_after)
        self.assertIsNone(assessment.eval_delta)
        self.assertIsNone(assessment.best_move)
        self.assertEqual(assessment.principal_variation, ())
        self.assertIsNone(assessment.depth)
        self.assertIsNone(assessment.eval_delta_for_event_side)
        self.assertIsNone(assessment.impact_magnitude)
        self.assertIsNone(assessment.candidate_eval_after)
        self.assertIsNone(assessment.candidate_move_uci)
        self.assertIsNone(assessment.candidate_after_fen)
        self.assertIsNone(assessment.event_impact_for_side)
        self.assertIsNone(assessment.score_before)
        self.assertIsNone(assessment.score_after)
        self.assertIsNone(assessment.candidate_score_after)
        self.assertEqual(assessment.event_score_kind, "unavailable")
        self.assertIsNone(assessment.event_impact_rank_for_side)
        self.assertIsNone(assessment.impact_rank)

    def test_principal_variation_is_stored_as_tuple_of_chess_moves(self) -> None:
        principal_variation = (
            chess.Move.from_uci("d2d4"),
            chess.Move.from_uci("d7d5"),
        )

        assessment = EngineAssessment(
            eval_before=0,
            eval_after=10,
            eval_delta=10,
            best_move=principal_variation[0],
            principal_variation=principal_variation,
            depth=8,
        )

        self.assertIsInstance(assessment.principal_variation, tuple)
        self.assertTrue(
            all(isinstance(move, chess.Move) for move in assessment.principal_variation)
        )

    def test_model_is_frozen(self) -> None:
        assessment = EngineAssessment(
            eval_before=0,
            eval_after=0,
            eval_delta=0,
            best_move=None,
            principal_variation=(),
            depth=1,
        )

        with self.assertRaises(FrozenInstanceError):
            assessment.depth = 2  # type: ignore[misc]

    def test_model_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(EngineAssessment)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_model_does_not_import_or_call_stockfish(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "models"
            / "engine_assessment.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("chess.engine", source)

    def test_engine_assessment_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.EngineAssessment, EngineAssessment)
