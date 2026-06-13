import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import chess

from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    VerifiedEvent,
    WeaknessProfile,
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
            eval_after=-100,
            eval_delta=-100,
            best_move=None,
            principal_variation=(),
            depth=10,
        ),
    )


def make_detected_pattern() -> DetectedPattern:
    return DetectedPattern(
        pattern_type="hanging_piece_created",
        frequency=3,
        severity=100.0,
        supporting_events=(make_verified_event(),),
    )


def make_weakness_profile() -> WeaknessProfile:
    pattern = make_detected_pattern()
    return WeaknessProfile(
        strengths=(),
        weaknesses=(pattern,),
        recurring_themes=(pattern,),
    )


class CoachingMomentTest(unittest.TestCase):
    def test_can_be_constructed_with_all_fields(self) -> None:
        verified_event = make_verified_event()
        pattern = make_detected_pattern()
        profile = make_weakness_profile()

        moment = CoachingMoment(
            title="Defend loose pieces",
            explanation="Your bishop became a target because it had no defender.",
            supporting_evidence=(verified_event, pattern, profile),
            position_reference=chess.STARTING_FEN,
            highlights=(chess.E4, chess.D5),
        )

        self.assertEqual(moment.title, "Defend loose pieces")
        self.assertEqual(
            moment.explanation,
            "Your bishop became a target because it had no defender.",
        )
        self.assertEqual(moment.supporting_evidence, (verified_event, pattern, profile))
        self.assertEqual(moment.position_reference, chess.STARTING_FEN)
        self.assertEqual(moment.highlights, (chess.E4, chess.D5))

    def test_supports_empty_highlights(self) -> None:
        moment = CoachingMoment(
            title="Review the position",
            explanation="Look for undefended pieces before moving.",
            supporting_evidence=(),
            position_reference=chess.STARTING_FEN,
            highlights=(),
        )

        self.assertEqual(moment.highlights, ())

    def test_supports_missing_position_reference(self) -> None:
        moment = CoachingMoment(
            title="Pattern summary",
            explanation="This pattern appeared several times.",
            supporting_evidence=(),
            position_reference=None,
            highlights=(),
        )

        self.assertIsNone(moment.position_reference)

    def test_model_is_frozen(self) -> None:
        moment = CoachingMoment(
            title="Frozen lesson",
            explanation="This text is stored but not generated here.",
            supporting_evidence=(),
            position_reference=None,
            highlights=(),
        )

        with self.assertRaises(FrozenInstanceError):
            moment.title = "Changed"  # type: ignore[misc]

    def test_allows_human_facing_title_and_explanation(self) -> None:
        moment = CoachingMoment(
            title="Notice undefended pieces",
            explanation="Pause before moving and ask what changed defensively.",
            supporting_evidence=(),
            position_reference=None,
            highlights=(),
        )

        self.assertEqual(moment.title, "Notice undefended pieces")
        self.assertEqual(
            moment.explanation,
            "Pause before moving and ask what changed defensively.",
        )

    def test_supporting_evidence_is_stored_as_tuple(self) -> None:
        evidence = (make_verified_event(), make_detected_pattern(), make_weakness_profile())

        moment = CoachingMoment(
            title="Evidence-backed lesson",
            explanation="This lesson is grounded in structured evidence.",
            supporting_evidence=evidence,
            position_reference=None,
            highlights=(),
        )

        self.assertIsInstance(moment.supporting_evidence, tuple)
        self.assertEqual(moment.supporting_evidence, evidence)

    def test_highlights_are_stored_as_tuple_of_chess_squares(self) -> None:
        moment = CoachingMoment(
            title="Highlighted squares",
            explanation="The highlighted squares show the relevant pieces.",
            supporting_evidence=(),
            position_reference=None,
            highlights=(chess.C4, chess.F7),
        )

        self.assertIsInstance(moment.highlights, tuple)
        self.assertTrue(all(isinstance(square, int) for square in moment.highlights))

    def test_coaching_moment_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.CoachingMoment, CoachingMoment)

    def test_detected_event_still_has_no_human_facing_language_fields(self) -> None:
        field_names = {field.name for field in fields(DetectedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_model_source_does_not_reference_llms_stockfish_or_engine(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "models"
            / "coaching_moment.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
