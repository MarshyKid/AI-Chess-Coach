import unittest
from dataclasses import FrozenInstanceError, fields

import chess

from ai_chess_coach.models import (
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    VerifiedEvent,
)


def make_verified_event() -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type="hanging_piece_created",
            side=chess.WHITE,
            move=chess.Move.from_uci("e2e4"),
            position=chess.Board(),
            squares=(chess.E4,),
            evidence={},
            severity=1.0,
        ),
        engine_assessment=EngineAssessment(
            eval_before=0,
            eval_after=50,
            eval_delta=50,
            best_move=None,
            principal_variation=(),
            depth=10,
        ),
    )


class DetectedPatternTest(unittest.TestCase):
    def test_can_be_constructed_with_all_fields(self) -> None:
        event = make_verified_event()

        pattern = DetectedPattern(
            pattern_type="hanging_piece_created",
            frequency=1,
            severity=50.0,
            supporting_events=(event,),
        )

        self.assertEqual(pattern.pattern_type, "hanging_piece_created")
        self.assertEqual(pattern.frequency, 1)
        self.assertEqual(pattern.severity, 50.0)
        self.assertEqual(pattern.supporting_events, (event,))

    def test_model_is_frozen(self) -> None:
        pattern = DetectedPattern(
            pattern_type="fork_missed",
            frequency=1,
            severity=1.0,
            supporting_events=(make_verified_event(),),
        )

        with self.assertRaises(FrozenInstanceError):
            pattern.frequency = 2  # type: ignore[misc]

    def test_model_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(DetectedPattern)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_detected_pattern_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.DetectedPattern, DetectedPattern)
