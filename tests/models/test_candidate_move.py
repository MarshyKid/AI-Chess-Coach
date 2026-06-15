import unittest
from dataclasses import FrozenInstanceError, fields

import chess

from ai_chess_coach.models import CandidateMove


class CandidateMoveTest(unittest.TestCase):
    def test_can_be_constructed_with_all_fields(self) -> None:
        candidate = CandidateMove(
            move_uci="f2d3",
            move_san="Nd3+",
            start_fen=chess.STARTING_FEN,
            side=chess.WHITE,
        )

        self.assertEqual(candidate.move_uci, "f2d3")
        self.assertEqual(candidate.move_san, "Nd3+")
        self.assertEqual(candidate.start_fen, chess.STARTING_FEN)
        self.assertEqual(candidate.side, chess.WHITE)

    def test_supports_missing_san(self) -> None:
        candidate = CandidateMove(
            move_uci="f2d3",
            move_san=None,
            start_fen=chess.STARTING_FEN,
            side=chess.WHITE,
        )

        self.assertIsNone(candidate.move_san)

    def test_model_is_frozen(self) -> None:
        candidate = CandidateMove(
            move_uci="f2d3",
            move_san="Nd3+",
            start_fen=chess.STARTING_FEN,
            side=chess.WHITE,
        )

        with self.assertRaises(FrozenInstanceError):
            candidate.move_uci = "a1a2"  # type: ignore[misc]

    def test_model_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(CandidateMove)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_candidate_move_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.CandidateMove, CandidateMove)
