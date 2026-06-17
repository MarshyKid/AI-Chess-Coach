"""Tests for the PGN analysis CLI."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import chess

from ai_chess_coach.cli import analyze_pgn
from ai_chess_coach.detectors import (
    ForkDetector,
    HangingPieceDetector,
    KnightOutpostDetector,
)
from ai_chess_coach.engine import StockfishUnavailableError
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    EngineScore,
    EventMetadata,
    GameAnalysisResult,
    MoveTransition,
    VerifiedEvent,
    WeaknessProfile,
)


class FakeEngine:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakePipeline:
    def __init__(self, result: GameAnalysisResult | None = None) -> None:
        self.pgn_texts: list[str] = []
        self.result = result or empty_result()

    def analyze_pgn(self, pgn_text: str) -> GameAnalysisResult:
        self.pgn_texts.append(pgn_text)
        return self.result


class RaisingPipeline:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def analyze_pgn(self, pgn_text: str) -> GameAnalysisResult:
        raise self.exc


class AnalyzePgnCliTest(unittest.TestCase):
    def test_format_result_includes_all_sections(self) -> None:
        result = populated_result()

        output = analyze_pgn.format_result(result)

        self.assertIn("AI Chess Coach Analysis", output)
        self.assertIn("Moves: 1", output)
        self.assertIn("Detected Events (1)", output)
        self.assertIn("- hanging_piece_created side=white move=e2e4 squares=e4 severity=1.5", output)
        self.assertIn("Verified Events (1)", output)
        self.assertIn(
            "- hanging_piece_created eval_before=10 eval_after=-40 eval_delta=-50 "
            "event_impact_for_side=-50 impact_magnitude=50 score_kind=centipawn "
            "event_impact_rank_for_side=-50 impact_rank=50 candidate_move=none "
            "score_before=10cp score_after=-40cp candidate_score_after=none "
            "best_move=e2e4 depth=12",
            output,
        )
        self.assertIn("Detected Patterns (1)", output)
        self.assertIn(
            "- hanging_piece_created frequency=1 severity=50.0 supporting_events=1",
            output,
        )
        self.assertIn("- High-Impact Strengths: none", output)
        self.assertIn("- Execution Strengths: fork_created", output)
        self.assertIn("- Weaknesses: hanging_piece_created", output)
        self.assertIn("Coaching Moments (1)", output)
        self.assertIn("- Hanging Piece Created", output)
        self.assertIn("  Position:", output)
        self.assertIn("  Highlights: e4", output)
        self.assertIn("  Summary: A verified event was found.", output)
        self.assertIn("  Details:", output)
        self.assertIn(
            "    - hanging_piece_created: white pawn on e4 became hanging; "
            "attackers: d5; defenders: none",
            output,
        )

    def test_format_result_handles_empty_sections(self) -> None:
        output = analyze_pgn.format_result(empty_result())

        self.assertIn("Moves: 0", output)
        self.assertIn("Detected Events (0)", output)
        self.assertIn("Verified Events (0)", output)
        self.assertIn("Detected Patterns (0)", output)
        self.assertIn("- High-Impact Strengths: none", output)
        self.assertIn("- Execution Strengths: none", output)
        self.assertIn("- Weaknesses: none", output)
        self.assertIn("- Recurring Themes: none", output)
        self.assertIn("Coaching Moments (0)", output)

    def test_format_result_keeps_raw_verified_events_separate_from_selected_moments(
        self,
    ) -> None:
        base_result = populated_result()
        result = GameAnalysisResult(
            transitions=base_result.transitions,
            detected_events=base_result.detected_events,
            verified_events=base_result.verified_events * 2,
            detected_patterns=base_result.detected_patterns,
            weakness_profile=base_result.weakness_profile,
            coaching_moments=base_result.coaching_moments,
        )

        output = analyze_pgn.format_result(result)

        self.assertIn("Verified Events (2)", output)
        self.assertIn("Coaching Moments (1)", output)
        self.assertEqual(output.count("    - hanging_piece_created:"), 1)

    def test_format_result_labels_mate_rank_values_without_centipawn_language(self) -> None:
        base_result = populated_result()
        event = base_result.verified_events[0].event
        verified_event = VerifiedEvent(
            event=event,
            engine_assessment=EngineAssessment(
                eval_before=0,
                eval_after=None,
                eval_delta=None,
                best_move=event.move,
                principal_variation=(event.move,),
                depth=12,
                score_before=EngineScore(centipawns=0),
                score_after=EngineScore(mate=-2),
                event_score_kind="mate",
                event_impact_rank_for_side=-9_999_998,
                impact_rank=9_999_998,
            ),
        )
        result = GameAnalysisResult(
            transitions=base_result.transitions,
            detected_events=base_result.detected_events,
            verified_events=(verified_event,),
            detected_patterns=base_result.detected_patterns,
            weakness_profile=base_result.weakness_profile,
            coaching_moments=(),
        )

        output = analyze_pgn.format_result(result)

        self.assertIn("score_kind=mate", output)
        self.assertIn("event_impact_rank_for_side=-9999998", output)
        self.assertIn("impact_rank=9999998", output)
        self.assertIn("score_after=mate-2", output)
        self.assertNotIn("rank_for_side=-9999998 centipawns", output)
        self.assertNotIn("impact_rank=9999998 centipawns", output)

    def test_main_success_reads_file_runs_pipeline_prints_result_and_closes_engine(self) -> None:
        fake_engine = FakeEngine()
        fake_pipeline = FakePipeline(result=empty_result())
        pgn_text = '[Event "CLI Test"]\n\n1. e4 *\n'

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write(pgn_text)
            pgn_file.flush()
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(analyze_pgn, "StockfishEngine", return_value=fake_engine),
                patch.object(
                    analyze_pgn,
                    "build_default_game_analysis_pipeline",
                    return_value=fake_pipeline,
                ) as pipeline_builder,
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = analyze_pgn.main([pgn_file.name])

        self.assertEqual(0, exit_code)
        self.assertEqual([pgn_text], fake_pipeline.pgn_texts)
        pipeline_builder.assert_called_once_with(fake_engine)
        self.assertTrue(fake_engine.closed)
        self.assertIn("AI Chess Coach Analysis", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())

    def test_main_closes_engine_when_analysis_raises_value_error(self) -> None:
        fake_engine = FakeEngine()
        fake_pipeline = RaisingPipeline(ValueError("bad pgn"))

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write("bad")
            pgn_file.flush()
            stderr = io.StringIO()
            with (
                patch.object(analyze_pgn, "StockfishEngine", return_value=fake_engine),
                patch.object(
                    analyze_pgn,
                    "build_default_game_analysis_pipeline",
                    return_value=fake_pipeline,
                ),
                redirect_stderr(stderr),
            ):
                exit_code = analyze_pgn.main([pgn_file.name])

        self.assertEqual(3, exit_code)
        self.assertTrue(fake_engine.closed)
        self.assertIn("Invalid PGN or analysis input: bad pgn", stderr.getvalue())

    def test_main_missing_file_returns_one(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = analyze_pgn.main(["/definitely/not/a/game.pgn"])

        self.assertEqual(1, exit_code)
        self.assertIn("PGN file not found:", stderr.getvalue())

    def test_main_invalid_pgn_returns_three(self) -> None:
        fake_pipeline = RaisingPipeline(ValueError("empty PGN"))

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write("   ")
            pgn_file.flush()
            stderr = io.StringIO()
            with (
                patch.object(analyze_pgn, "StockfishEngine", return_value=FakeEngine()),
                patch.object(
                    analyze_pgn,
                    "build_default_game_analysis_pipeline",
                    return_value=fake_pipeline,
                ),
                redirect_stderr(stderr),
            ):
                exit_code = analyze_pgn.main([pgn_file.name])

        self.assertEqual(3, exit_code)
        self.assertIn("Invalid PGN or analysis input: empty PGN", stderr.getvalue())

    def test_main_stockfish_unavailable_returns_two(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write('[Event "CLI Test"]\n\n1. e4 *\n')
            pgn_file.flush()
            stderr = io.StringIO()
            with (
                patch.object(
                    analyze_pgn,
                    "StockfishEngine",
                    side_effect=StockfishUnavailableError("missing"),
                ),
                redirect_stderr(stderr),
            ):
                exit_code = analyze_pgn.main([pgn_file.name])

        self.assertEqual(2, exit_code)
        self.assertIn("Stockfish unavailable: missing", stderr.getvalue())

    def test_default_detector_registry_contains_existing_detectors_in_order(self) -> None:
        registry = analyze_pgn.build_default_detector_registry()

        self.assertEqual(
            (HangingPieceDetector, ForkDetector, KnightOutpostDetector),
            tuple(type(detector) for detector in registry.registered_detectors()),
        )

    def test_console_script_is_declared(self) -> None:
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(
            "ai_chess_coach.cli.analyze_pgn:main",
            pyproject["project"]["scripts"]["ai-chess-coach-analyze"],
        )

    def test_cli_source_respects_architecture_boundaries(self) -> None:
        source = Path("src/ai_chess_coach/cli/analyze_pgn.py").read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("openai", lower_source)
        self.assertNotIn("llm", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("attackers", lower_source)
        self.assertNotIn("def detect", lower_source)


def populated_result() -> GameAnalysisResult:
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    before_position = board.copy(stack=False)
    san = board.san(move)
    board.push(move)
    after_position = board.copy(stack=False)
    transition = MoveTransition(
        ply=1,
        san=san,
        move=move,
        before_position=before_position,
        after_position=after_position,
    )
    event = DetectedEvent(
        event_type="hanging_piece_created",
        side=chess.WHITE,
        move=move,
        position=after_position,
        squares=(chess.E4,),
        metadata=EventMetadata(
            before_fen=before_position.fen(),
            after_fen=after_position.fen(),
            move_uci=move.uci(),
            move_san=san,
            ply=transition.ply,
        ),
        evidence={
            "piece_square": "e4",
            "piece": "P",
            "piece_color": "white",
            "attackers": ("d5",),
            "defenders": (),
        },
        severity=1.5,
    )
    verified_event = VerifiedEvent(
        event=event,
        engine_assessment=EngineAssessment(
            eval_before=10,
            eval_after=-40,
            eval_delta=-50,
            best_move=move,
            principal_variation=(move,),
            depth=12,
            eval_delta_for_event_side=-50,
            impact_magnitude=50,
            event_impact_for_side=-50,
            score_before=EngineScore(centipawns=10),
            score_after=EngineScore(centipawns=-40),
            event_score_kind="centipawn",
            event_impact_rank_for_side=-50,
            impact_rank=50,
        ),
    )
    pattern = DetectedPattern(
        pattern_type="hanging_piece_created",
        frequency=1,
        severity=50.0,
        supporting_events=(verified_event,),
    )
    profile = WeaknessProfile(
        strengths=(),
        weaknesses=(pattern,),
        recurring_themes=(pattern,),
        execution_strengths=(
            DetectedPattern(
                pattern_type="fork_created",
                frequency=1,
                severity=1.0,
                supporting_events=(),
            ),
        ),
    )
    moment = CoachingMoment(
        title="Hanging Piece Created",
        explanation="A verified event was found.",
        supporting_evidence=(verified_event,),
        position_reference=after_position.fen(),
        highlights=(chess.E4,),
    )

    return GameAnalysisResult(
        transitions=(transition,),
        detected_events=(event,),
        verified_events=(verified_event,),
        detected_patterns=(pattern,),
        weakness_profile=profile,
        coaching_moments=(moment,),
    )


def empty_result() -> GameAnalysisResult:
    return GameAnalysisResult(
        transitions=(),
        detected_events=(),
        verified_events=(),
        detected_patterns=(),
        weakness_profile=WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=()),
        coaching_moments=(),
    )
