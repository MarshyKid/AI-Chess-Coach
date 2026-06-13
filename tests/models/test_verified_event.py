import unittest
from dataclasses import FrozenInstanceError, fields

import chess

from ai_chess_coach.models import DetectedEvent, EngineAssessment, VerifiedEvent


def make_event() -> DetectedEvent:
    return DetectedEvent(
        event_type="hanging_piece_created",
        side=chess.WHITE,
        move=chess.Move.from_uci("e2e4"),
        position=chess.Board(),
        squares=(chess.E4,),
        evidence={
            "before_fen": chess.STARTING_FEN,
            "after_fen": chess.Board().fen(),
        },
        severity=1.0,
    )


def make_assessment() -> EngineAssessment:
    return EngineAssessment(
        eval_before=10,
        eval_after=35,
        eval_delta=25,
        best_move=chess.Move.from_uci("e2e4"),
        principal_variation=(chess.Move.from_uci("e2e4"),),
        depth=12,
    )


class VerifiedEventTest(unittest.TestCase):
    def test_can_be_constructed_with_event_and_engine_assessment(self) -> None:
        event = make_event()
        assessment = make_assessment()

        verified_event = VerifiedEvent(event=event, engine_assessment=assessment)

        self.assertIs(verified_event.event, event)
        self.assertIs(verified_event.engine_assessment, assessment)

    def test_model_is_frozen(self) -> None:
        verified_event = VerifiedEvent(
            event=make_event(),
            engine_assessment=make_assessment(),
        )

        with self.assertRaises(FrozenInstanceError):
            verified_event.engine_assessment = make_assessment()  # type: ignore[misc]

    def test_model_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(VerifiedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_verified_event_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.VerifiedEvent, VerifiedEvent)
