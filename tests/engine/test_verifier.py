from pathlib import Path
import unittest
from dataclasses import fields
from unittest.mock import Mock, call

import chess
import chess.engine

from ai_chess_coach.engine import (
    EventVerificationError,
    EventVerifier,
    StockfishAnalysis,
)
from ai_chess_coach.models import DetectedEvent, VerifiedEvent


def make_event(
    *,
    before_fen: object = chess.STARTING_FEN,
    after_fen: object = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
) -> DetectedEvent:
    return DetectedEvent(
        event_type="hanging_piece_created",
        side=chess.WHITE,
        move=chess.Move.from_uci("e2e4"),
        position=chess.Board(),
        squares=(chess.E4,),
        evidence={
            "before_fen": before_fen,
            "after_fen": after_fen,
        },
        severity=1.0,
    )


def analysis(
    score: chess.engine.PovScore | None,
    *,
    best_move: chess.Move | None = None,
    principal_variation: tuple[chess.Move, ...] = (),
    depth: int | None = None,
) -> StockfishAnalysis:
    return StockfishAnalysis(
        fen=chess.STARTING_FEN,
        score=score,
        best_move=best_move,
        principal_variation=principal_variation,
        depth=depth,
    )


class EventVerifierTest(unittest.TestCase):
    def test_verify_returns_verified_event(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)),
        )

        verified_event = EventVerifier(engine).verify(make_event())

        self.assertIsInstance(verified_event, VerifiedEvent)

    def test_uses_injected_engine_and_event_fens(self) -> None:
        engine = Mock()
        before_fen = chess.STARTING_FEN
        after_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)),
        )

        EventVerifier(engine).verify(make_event(before_fen=before_fen, after_fen=after_fen))

        self.assertEqual(
            engine.evaluate_fen.call_args_list,
            [call(before_fen), call(after_fen)],
        )

    def test_computes_eval_delta_from_white_perspective_centipawns(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(-15), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(35), chess.WHITE)),
        )

        verified_event = EventVerifier(engine).verify(make_event())

        assessment = verified_event.engine_assessment
        self.assertEqual(assessment.eval_before, -15)
        self.assertEqual(assessment.eval_after, 35)
        self.assertEqual(assessment.eval_delta, 50)

    def test_copies_best_move_principal_variation_and_depth_from_before_analysis(self) -> None:
        engine = Mock()
        best_move = chess.Move.from_uci("e2e4")
        principal_variation = (
            best_move,
            chess.Move.from_uci("e7e5"),
        )
        engine.evaluate_fen.side_effect = (
            analysis(
                chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE),
                best_move=best_move,
                principal_variation=principal_variation,
                depth=14,
            ),
            analysis(
                chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE),
                best_move=chess.Move.from_uci("d7d5"),
                principal_variation=(chess.Move.from_uci("d7d5"),),
                depth=8,
            ),
        )

        assessment = EventVerifier(engine).verify(make_event()).engine_assessment

        self.assertEqual(assessment.best_move, best_move)
        self.assertEqual(assessment.principal_variation, principal_variation)
        self.assertEqual(assessment.depth, 14)

    def test_unavailable_scores_produce_none_eval_and_delta(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(None),
            analysis(chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(make_event()).engine_assessment

        self.assertIsNone(assessment.eval_before)
        self.assertEqual(assessment.eval_after, 20)
        self.assertIsNone(assessment.eval_delta)

    def test_mate_scores_produce_none_eval_and_delta(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(make_event()).engine_assessment

        self.assertIsNone(assessment.eval_before)
        self.assertEqual(assessment.eval_after, 20)
        self.assertIsNone(assessment.eval_delta)

    def test_missing_before_fen_raises_event_verification_error(self) -> None:
        event = make_event()
        event = DetectedEvent(
            event_type=event.event_type,
            side=event.side,
            move=event.move,
            position=event.position,
            squares=event.squares,
            evidence={"after_fen": event.evidence["after_fen"]},
            severity=event.severity,
        )

        with self.assertRaisesRegex(EventVerificationError, "before_fen"):
            EventVerifier(Mock()).verify(event)

    def test_missing_after_fen_raises_event_verification_error(self) -> None:
        event = make_event()
        event = DetectedEvent(
            event_type=event.event_type,
            side=event.side,
            move=event.move,
            position=event.position,
            squares=event.squares,
            evidence={"before_fen": event.evidence["before_fen"]},
            severity=event.severity,
        )

        with self.assertRaisesRegex(EventVerificationError, "after_fen"):
            EventVerifier(Mock()).verify(event)

    def test_non_string_fens_raise_event_verification_error(self) -> None:
        with self.assertRaisesRegex(EventVerificationError, "before_fen"):
            EventVerifier(Mock()).verify(make_event(before_fen=object()))

        with self.assertRaisesRegex(EventVerificationError, "after_fen"):
            EventVerifier(Mock()).verify(make_event(after_fen=object()))

    def test_engine_exceptions_propagate(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = RuntimeError("engine failed")

        with self.assertRaisesRegex(RuntimeError, "engine failed"):
            EventVerifier(engine).verify(make_event())

    def test_verification_does_not_reject_events_based_on_eval_delta(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(500), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(-500), chess.WHITE)),
        )

        verified_event = EventVerifier(engine).verify(make_event())

        self.assertIsInstance(verified_event, VerifiedEvent)
        self.assertEqual(verified_event.engine_assessment.eval_delta, -1000)

    def test_verified_event_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(VerifiedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_event_verifier_is_exported_from_engine_package(self) -> None:
        import ai_chess_coach.engine as engine

        self.assertIs(engine.EventVerifier, EventVerifier)
        self.assertIs(engine.EventVerificationError, EventVerificationError)

    def test_detectors_do_not_import_engine_or_stockfish(self) -> None:
        detector_dir = Path(__file__).parents[2] / "src" / "ai_chess_coach" / "detectors"

        for detector_file in detector_dir.glob("*.py"):
            source = detector_file.read_text(encoding="utf-8").lower()
            self.assertNotIn("ai_chess_coach.engine", source, detector_file.name)
            self.assertNotIn("stockfish", source, detector_file.name)

    def test_verifier_source_does_not_introduce_llm_calls(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "engine"
            / "verifier.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
