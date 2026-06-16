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
from ai_chess_coach.models import (
    CandidateMove,
    DetectedEvent,
    EngineScore,
    EventMetadata,
    MATE_RANK_BASE,
    VerifiedEvent,
)


def make_event(
    *,
    event_type: str = "hanging_piece_created",
    side: chess.Color = chess.WHITE,
    before_fen: str = chess.STARTING_FEN,
    after_fen: str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    move_uci: str = "e2e4",
    move_san: str = "e4",
    candidate_move: CandidateMove | None = None,
) -> DetectedEvent:
    return DetectedEvent(
        event_type=event_type,
        side=side,
        move=chess.Move.from_uci(move_uci),
        position=chess.Board(),
        squares=(chess.E4,),
        metadata=EventMetadata(
            before_fen=before_fen,
            after_fen=after_fen,
            move_uci=move_uci,
            move_san=move_san,
            ply=1,
        ),
        evidence={},
        severity=1.0,
        candidate_move=candidate_move,
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


def candidate_after_fen(start_fen: str, move_uci: str) -> str:
    board = chess.Board(start_fen)
    board.push(chess.Move.from_uci(move_uci))
    return board.fen()


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
        self.assertEqual(assessment.score_before, EngineScore(centipawns=-15))
        self.assertEqual(assessment.score_after, EngineScore(centipawns=35))
        self.assertEqual(assessment.event_score_kind, "centipawn")

    def test_computes_side_aware_delta_for_white_attributed_event(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(-15), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(35), chess.WHITE)),
        )

        assessment = (
            EventVerifier(engine).verify(make_event(side=chess.WHITE)).engine_assessment
        )

        self.assertEqual(assessment.eval_delta, 50)
        self.assertEqual(assessment.eval_delta_for_event_side, 50)
        self.assertEqual(assessment.event_impact_for_side, 50)
        self.assertEqual(assessment.impact_magnitude, 50)
        self.assertEqual(assessment.event_impact_rank_for_side, 50)
        self.assertEqual(assessment.impact_rank, 50)

    def test_computes_side_aware_delta_for_black_attributed_event(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(-15), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(35), chess.WHITE)),
        )

        assessment = (
            EventVerifier(engine).verify(make_event(side=chess.BLACK)).engine_assessment
        )

        self.assertEqual(assessment.eval_delta, 50)
        self.assertEqual(assessment.eval_delta_for_event_side, -50)
        self.assertEqual(assessment.event_impact_for_side, -50)
        self.assertEqual(assessment.impact_magnitude, 50)
        self.assertEqual(assessment.event_impact_rank_for_side, -50)
        self.assertEqual(assessment.impact_rank, 50)

    def test_black_attributed_event_improves_when_white_perspective_delta_is_negative(
        self,
    ) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(-20), chess.WHITE)),
        )

        assessment = (
            EventVerifier(engine).verify(make_event(side=chess.BLACK)).engine_assessment
        )

        self.assertEqual(assessment.eval_delta, -40)
        self.assertEqual(assessment.eval_delta_for_event_side, 40)
        self.assertEqual(assessment.event_impact_for_side, 40)
        self.assertEqual(assessment.impact_magnitude, 40)

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

    def test_missed_candidate_event_compares_actual_move_against_candidate(self) -> None:
        engine = Mock()
        candidate_fen = candidate_after_fen(chess.STARTING_FEN, "d2d4")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(400), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_missed",
                candidate_move=CandidateMove(
                    move_uci="d2d4",
                    move_san="d4",
                    start_fen=chess.STARTING_FEN,
                    side=chess.WHITE,
                ),
            )
        ).engine_assessment

        self.assertEqual(engine.evaluate_fen.call_args_list[-1], call(candidate_fen))
        self.assertEqual(assessment.eval_delta, 100)
        self.assertEqual(assessment.candidate_eval_after, 400)
        self.assertEqual(assessment.candidate_after_fen, candidate_fen)
        self.assertEqual(assessment.candidate_move_uci, "d2d4")
        self.assertEqual(assessment.event_impact_for_side, -300)
        self.assertEqual(assessment.impact_magnitude, 300)
        self.assertEqual(assessment.candidate_score_after, EngineScore(centipawns=400))
        self.assertEqual(assessment.event_score_kind, "centipawn")
        self.assertEqual(assessment.event_impact_rank_for_side, -300)
        self.assertEqual(assessment.impact_rank, 300)

    def test_knight_outpost_missed_uses_missed_candidate_strategy(self) -> None:
        engine = Mock()
        candidate_fen = candidate_after_fen(chess.STARTING_FEN, "d2d4")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(250), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="knight_outpost_missed",
                candidate_move=CandidateMove(
                    move_uci="d2d4",
                    move_san="d4",
                    start_fen=chess.STARTING_FEN,
                    side=chess.WHITE,
                ),
            )
        ).engine_assessment

        self.assertEqual(engine.evaluate_fen.call_args_list[-1], call(candidate_fen))
        self.assertEqual(assessment.event_impact_for_side, -150)
        self.assertEqual(assessment.impact_magnitude, 150)

    def test_missed_candidate_worse_than_actual_move_has_positive_event_impact(
        self,
    ) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(330), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(-600), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_missed",
                candidate_move=CandidateMove(
                    move_uci="d2d4",
                    move_san="d4",
                    start_fen=chess.STARTING_FEN,
                    side=chess.WHITE,
                ),
            )
        ).engine_assessment

        self.assertEqual(assessment.event_impact_for_side, 930)
        self.assertEqual(assessment.impact_magnitude, 930)

    def test_allowed_response_event_compares_opponent_candidate_to_actual_after(
        self,
    ) -> None:
        engine = Mock()
        after_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        candidate_fen = candidate_after_fen(after_fen, "e7e5")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(-200), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_allowed",
                after_fen=after_fen,
                candidate_move=CandidateMove(
                    move_uci="e7e5",
                    move_san="e5",
                    start_fen=after_fen,
                    side=chess.BLACK,
                ),
            )
        ).engine_assessment

        self.assertEqual(engine.evaluate_fen.call_args_list[-1], call(candidate_fen))
        self.assertEqual(assessment.candidate_eval_after, -200)
        self.assertEqual(assessment.candidate_after_fen, candidate_fen)
        self.assertEqual(assessment.event_impact_for_side, -300)
        self.assertEqual(assessment.impact_magnitude, 300)

    def test_missed_candidate_black_side_flips_perspective(self) -> None:
        engine = Mock()
        before_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        after_fen = candidate_after_fen(before_fen, "e7e6")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(-200), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_missed",
                side=chess.BLACK,
                before_fen=before_fen,
                after_fen=after_fen,
                move_uci="e7e6",
                move_san="e6",
                candidate_move=CandidateMove(
                    move_uci="e7e5",
                    move_san="e5",
                    start_fen=before_fen,
                    side=chess.BLACK,
                ),
            )
        ).engine_assessment

        self.assertEqual(assessment.event_impact_for_side, -300)
        self.assertEqual(assessment.impact_magnitude, 300)

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
        self.assertIsNone(assessment.eval_delta_for_event_side)
        self.assertIsNone(assessment.impact_magnitude)
        self.assertIsNone(assessment.event_impact_for_side)
        self.assertEqual(assessment.score_before, EngineScore())
        self.assertEqual(assessment.score_after, EngineScore(centipawns=20))
        self.assertEqual(assessment.event_score_kind, "unavailable")
        self.assertIsNone(assessment.event_impact_rank_for_side)
        self.assertIsNone(assessment.impact_rank)

    def test_mate_scores_are_represented_and_ranked_for_actual_move(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(make_event()).engine_assessment

        self.assertEqual(assessment.score_before, EngineScore(centipawns=0))
        self.assertEqual(assessment.score_after, EngineScore(mate=2))
        self.assertEqual(assessment.event_score_kind, "mate")
        self.assertEqual(assessment.event_impact_rank_for_side, MATE_RANK_BASE - 2)
        self.assertEqual(assessment.impact_rank, MATE_RANK_BASE - 2)
        self.assertEqual(assessment.eval_before, 0)
        self.assertIsNone(assessment.eval_after)
        self.assertIsNone(assessment.eval_delta)
        self.assertIsNone(assessment.eval_delta_for_event_side)
        self.assertIsNone(assessment.event_impact_for_side)
        self.assertIsNone(assessment.impact_magnitude)

    def test_actual_move_mate_comparison_flips_for_black_side(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)),
        )

        assessment = (
            EventVerifier(engine).verify(make_event(side=chess.BLACK)).engine_assessment
        )

        self.assertEqual(assessment.event_score_kind, "mate")
        self.assertEqual(assessment.event_impact_rank_for_side, -MATE_RANK_BASE + 2)
        self.assertEqual(assessment.impact_rank, MATE_RANK_BASE - 2)
        self.assertIsNone(assessment.event_impact_for_side)
        self.assertIsNone(assessment.impact_magnitude)

    def test_mixed_mate_to_centipawn_actual_move_is_large_negative_rank(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(make_event()).engine_assessment

        self.assertEqual(assessment.event_score_kind, "mate")
        self.assertEqual(
            assessment.event_impact_rank_for_side,
            100 - (MATE_RANK_BASE - 2),
        )
        self.assertEqual(assessment.impact_rank, MATE_RANK_BASE - 102)

    def test_missed_candidate_can_compare_candidate_mate_from_before_position(self) -> None:
        engine = Mock()
        candidate_fen = candidate_after_fen(chess.STARTING_FEN, "d2d4")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Mate(2), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_missed",
                candidate_move=CandidateMove(
                    move_uci="d2d4",
                    move_san="d4",
                    start_fen=chess.STARTING_FEN,
                    side=chess.WHITE,
                ),
            )
        ).engine_assessment

        self.assertEqual(engine.evaluate_fen.call_args_list[-1], call(candidate_fen))
        self.assertEqual(assessment.candidate_score_after, EngineScore(mate=2))
        self.assertEqual(assessment.candidate_eval_after, None)
        self.assertEqual(assessment.event_score_kind, "mate")
        self.assertEqual(
            assessment.event_impact_rank_for_side,
            100 - (MATE_RANK_BASE - 2),
        )
        self.assertEqual(assessment.impact_rank, MATE_RANK_BASE - 102)
        self.assertIsNone(assessment.event_impact_for_side)
        self.assertIsNone(assessment.impact_magnitude)

    def test_missed_candidate_black_side_flips_mate_candidate_perspective(self) -> None:
        engine = Mock()
        before_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        after_fen = candidate_after_fen(before_fen, "e7e6")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Mate(-2), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_missed",
                side=chess.BLACK,
                before_fen=before_fen,
                after_fen=after_fen,
                move_uci="e7e6",
                move_san="e6",
                candidate_move=CandidateMove(
                    move_uci="e7e5",
                    move_san="e5",
                    start_fen=before_fen,
                    side=chess.BLACK,
                ),
            )
        ).engine_assessment

        actual_after_for_black = -100
        candidate_for_black = MATE_RANK_BASE - 2
        self.assertEqual(assessment.event_score_kind, "mate")
        self.assertEqual(
            assessment.event_impact_rank_for_side,
            actual_after_for_black - candidate_for_black,
        )
        self.assertEqual(assessment.impact_rank, abs(actual_after_for_black - candidate_for_black))

    def test_allowed_response_can_compare_opponent_candidate_mate_from_after_position(
        self,
    ) -> None:
        engine = Mock()
        after_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        candidate_fen = candidate_after_fen(after_fen, "e7e5")
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Mate(-2), chess.WHITE)),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_allowed",
                after_fen=after_fen,
                candidate_move=CandidateMove(
                    move_uci="e7e5",
                    move_san="e5",
                    start_fen=after_fen,
                    side=chess.BLACK,
                ),
            )
        ).engine_assessment

        self.assertEqual(engine.evaluate_fen.call_args_list[-1], call(candidate_fen))
        self.assertEqual(assessment.candidate_score_after, EngineScore(mate=-2))
        self.assertEqual(assessment.event_score_kind, "mate")
        self.assertEqual(
            assessment.event_impact_rank_for_side,
            (-MATE_RANK_BASE + 2) - 100,
        )
        self.assertEqual(assessment.impact_rank, MATE_RANK_BASE + 98)

    def test_candidate_score_unavailable_produces_none_event_impact(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
            analysis(None),
        )

        assessment = EventVerifier(engine).verify(
            make_event(
                event_type="fork_missed",
                candidate_move=CandidateMove(
                    move_uci="d2d4",
                    move_san="d4",
                    start_fen=chess.STARTING_FEN,
                    side=chess.WHITE,
                ),
            )
        ).engine_assessment

        self.assertIsNone(assessment.candidate_eval_after)
        self.assertIsNone(assessment.event_impact_for_side)
        self.assertIsNone(assessment.impact_magnitude)

    def test_missing_candidate_move_raises_for_candidate_event(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
        )

        with self.assertRaisesRegex(EventVerificationError, "Candidate move is required"):
            EventVerifier(engine).verify(make_event(event_type="fork_missed"))

    def test_candidate_start_fen_mismatch_raises(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
        )

        with self.assertRaisesRegex(EventVerificationError, "start FEN"):
            EventVerifier(engine).verify(
                make_event(
                    event_type="fork_missed",
                    candidate_move=CandidateMove(
                        move_uci="d2d4",
                        move_san="d4",
                        start_fen="different-fen",
                        side=chess.WHITE,
                    ),
                )
            )

    def test_invalid_candidate_uci_raises(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
        )

        with self.assertRaisesRegex(EventVerificationError, "UCI"):
            EventVerifier(engine).verify(
                make_event(
                    event_type="fork_missed",
                    candidate_move=CandidateMove(
                        move_uci="not-a-move",
                        move_san=None,
                        start_fen=chess.STARTING_FEN,
                        side=chess.WHITE,
                    ),
                )
            )

    def test_candidate_side_mismatch_raises(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
        )

        with self.assertRaisesRegex(EventVerificationError, "side"):
            EventVerifier(engine).verify(
                make_event(
                    event_type="fork_missed",
                    candidate_move=CandidateMove(
                        move_uci="d2d4",
                        move_san="d4",
                        start_fen=chess.STARTING_FEN,
                        side=chess.BLACK,
                    ),
                )
            )

    def test_illegal_candidate_move_raises(self) -> None:
        engine = Mock()
        engine.evaluate_fen.side_effect = (
            analysis(chess.engine.PovScore(chess.engine.Cp(0), chess.WHITE)),
            analysis(chess.engine.PovScore(chess.engine.Cp(100), chess.WHITE)),
        )

        with self.assertRaisesRegex(EventVerificationError, "not legal"):
            EventVerifier(engine).verify(
                make_event(
                    event_type="fork_missed",
                    candidate_move=CandidateMove(
                        move_uci="e7e5",
                        move_san="e5",
                        start_fen=chess.STARTING_FEN,
                        side=chess.WHITE,
                    ),
                )
            )

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

    def test_verifier_source_does_not_read_fens_from_event_evidence(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "engine"
            / "verifier.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn('evidence["before_fen"]', source)
        self.assertNotIn('evidence["after_fen"]', source)
        self.assertNotIn("evidence.get", source)
