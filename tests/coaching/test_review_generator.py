from pathlib import Path
import unittest

import chess

from ai_chess_coach.coaching import ReviewGenerator
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
)


def make_verified_event(
    event_type: str = "hanging_piece_created",
    *,
    move_uci: str = "e2e4",
    eval_delta: int | None = 100,
    impact_magnitude: int | None = None,
    event_severity: float = 1.0,
    after_fen: str = "after-fen",
    squares: tuple[chess.Square, ...] = (chess.E4,),
) -> VerifiedEvent:
    computed_impact_magnitude = (
        impact_magnitude
        if impact_magnitude is not None
        else abs(eval_delta)
        if eval_delta is not None
        else None
    )

    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=chess.WHITE,
            move=chess.Move.from_uci(move_uci),
            position=chess.Board(),
            squares=squares,
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen=after_fen,
                move_uci=move_uci,
                move_san=move_uci,
                ply=1,
            ),
            evidence={},
            severity=event_severity,
        ),
        engine_assessment=EngineAssessment(
            eval_before=0,
            eval_after=eval_delta,
            eval_delta=eval_delta,
            best_move=None,
            principal_variation=(),
            depth=10,
            eval_delta_for_event_side=eval_delta,
            impact_magnitude=computed_impact_magnitude,
        ),
    )


class ReviewGeneratorTest(unittest.TestCase):
    def test_generates_coaching_moments_from_verified_events(self) -> None:
        event = make_verified_event()

        moments = ReviewGenerator().generate((event,))

        self.assertIsInstance(moments, tuple)
        self.assertEqual(len(moments), 1)
        self.assertIsInstance(moments[0], CoachingMoment)

    def test_generated_moment_contains_expected_fields(self) -> None:
        event = make_verified_event(
            event_type="hanging_piece_created",
            eval_delta=-125,
            after_fen="verified-after-fen",
            squares=(chess.C4, chess.D5),
        )

        moment = ReviewGenerator().generate((event,))[0]

        self.assertEqual(moment.title, "Hanging Piece Created")
        self.assertIn("Hanging Piece Created", moment.explanation)
        self.assertIn("-125 centipawns", moment.explanation)
        self.assertEqual(moment.supporting_evidence, (event,))
        self.assertEqual(moment.position_reference, "verified-after-fen")
        self.assertEqual(moment.highlights, (chess.C4, chess.D5))

    def test_position_reference_uses_after_fen_when_available(self) -> None:
        event = make_verified_event(after_fen="after-position-fen")

        moment = ReviewGenerator().generate((event,))[0]

        self.assertEqual(moment.position_reference, "after-position-fen")

    def test_highlights_come_from_event_squares(self) -> None:
        event = make_verified_event(squares=(chess.A1, chess.H8))

        moment = ReviewGenerator().generate((event,))[0]

        self.assertEqual(moment.highlights, (chess.A1, chess.H8))

    def test_events_are_sorted_by_impact_magnitude_when_available(self) -> None:
        low = make_verified_event("fork_missed", eval_delta=50)
        high = make_verified_event("hanging_piece_lost", eval_delta=-200)

        moments = ReviewGenerator().generate((low, high))

        self.assertEqual([moment.supporting_evidence[0] for moment in moments], [high, low])

    def test_impact_magnitude_takes_precedence_over_raw_eval_delta(self) -> None:
        raw_eval_larger = make_verified_event(
            "fork_missed",
            eval_delta=500,
            impact_magnitude=25,
        )
        impact_larger = make_verified_event(
            "hanging_piece_lost",
            eval_delta=50,
            impact_magnitude=150,
        )

        moments = ReviewGenerator().generate((raw_eval_larger, impact_larger))

        self.assertEqual(
            [moment.supporting_evidence[0] for moment in moments],
            [impact_larger, raw_eval_larger],
        )

    def test_events_without_eval_delta_use_event_severity(self) -> None:
        low = make_verified_event("fork_missed", eval_delta=None, event_severity=0.5)
        high = make_verified_event("fork_allowed", eval_delta=None, event_severity=2.0)

        moments = ReviewGenerator().generate((low, high))

        self.assertEqual([moment.supporting_evidence[0] for moment in moments], [high, low])
        self.assertIn("detector severity 2.0", moments[0].explanation)

    def test_sorting_ties_use_event_type_then_move_uci(self) -> None:
        second = make_verified_event("fork_missed", move_uci="g1f3", eval_delta=100)
        first = make_verified_event("fork_allowed", move_uci="g1h3", eval_delta=-100)

        moments = ReviewGenerator().generate((second, first))

        self.assertEqual([moment.supporting_evidence[0] for moment in moments], [first, second])

    def test_empty_input_returns_empty_tuple(self) -> None:
        moments = ReviewGenerator().generate(())

        self.assertEqual(moments, ())

    def test_raw_pgn_strings_raise_type_error(self) -> None:
        with self.assertRaises(TypeError):
            ReviewGenerator().generate(("1. e4 e5",))  # type: ignore[arg-type]

    def test_raw_detected_events_raise_type_error(self) -> None:
        event = make_verified_event().event

        with self.assertRaises(TypeError):
            ReviewGenerator().generate((event,))  # type: ignore[arg-type]

    def test_review_generator_does_not_call_engine_llms_or_direct_chess_analysis(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "review_generator.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)
        self.assertNotIn('evidence["after_fen"]', source)
        self.assertNotIn('evidence.get("after_fen")', source)

    def test_review_generator_is_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(coaching.ReviewGenerator, ReviewGenerator)
