"""Analyze a PGN file through the backend pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import chess

from ai_chess_coach.coaching import format_coaching_moment_details
from ai_chess_coach.detectors import (
    DetectionPipeline,
    DetectorRegistry,
    ForkDetector,
    HangingPieceDetector,
    KnightOutpostDetector,
)
from ai_chess_coach.engine import EventVerifier, StockfishEngine, StockfishUnavailableError
from ai_chess_coach.models import DetectedPattern, GameAnalysisResult, VerifiedEvent
from ai_chess_coach.pipeline import GameAnalysisPipeline


def build_default_detector_registry() -> DetectorRegistry:
    """Build the default detector registry for the local demo."""

    registry = DetectorRegistry()
    registry.register(HangingPieceDetector())
    registry.register(ForkDetector())
    registry.register(KnightOutpostDetector())
    return registry


def build_default_detection_pipeline() -> DetectionPipeline:
    """Build the default detection pipeline."""

    return DetectionPipeline(build_default_detector_registry())


def build_default_game_analysis_pipeline(engine: StockfishEngine) -> GameAnalysisPipeline:
    """Build the default game analysis pipeline with an externally owned engine."""

    return GameAnalysisPipeline(
        detection_pipeline=build_default_detection_pipeline(),
        event_verifier=EventVerifier(engine),
    )


def format_result(result: GameAnalysisResult) -> str:
    """Format a game analysis result as deterministic plain text."""

    lines = [
        "AI Chess Coach Analysis",
        "",
        f"Moves: {len(result.transitions)}",
        "",
        f"Detected Events ({len(result.detected_events)})",
    ]
    lines.extend(_format_detected_event(event) for event in result.detected_events)
    lines.extend(
        [
            "",
            f"Verified Events ({len(result.verified_events)})",
        ]
    )
    lines.extend(_format_verified_event(event) for event in result.verified_events)
    lines.extend(
        [
            "",
            f"Detected Patterns ({len(result.detected_patterns)})",
        ]
    )
    lines.extend(_format_detected_pattern(pattern) for pattern in result.detected_patterns)
    lines.extend(
        [
            "",
            "Weakness Profile",
            f"- Strengths: {_pattern_types(result.weakness_profile.strengths)}",
            f"- Weaknesses: {_pattern_types(result.weakness_profile.weaknesses)}",
            f"- Recurring Themes: {_pattern_types(result.weakness_profile.recurring_themes)}",
            "",
            f"Coaching Moments ({len(result.coaching_moments)})",
        ]
    )

    for moment in result.coaching_moments:
        lines.append(f"- {moment.title}")
        if moment.position_reference is not None:
            lines.append(f"  Position: {moment.position_reference}")
        lines.append(f"  Highlights: {_squares(moment.highlights)}")
        lines.append(f"  Summary: {moment.explanation}")
        details = format_coaching_moment_details(moment)
        if details:
            lines.append("  Details:")
            lines.extend(f"    - {detail}" for detail in details)

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the PGN analysis demo CLI."""

    parser = argparse.ArgumentParser(
        prog="ai-chess-coach-analyze",
        description="Analyze one PGN file with the AI Chess Coach backend.",
    )
    parser.add_argument("pgn_file", help="Path to a PGN file.")
    args = parser.parse_args(argv)

    pgn_path = Path(args.pgn_file)
    if not pgn_path.is_file():
        print(f"PGN file not found: {pgn_path}", file=sys.stderr)
        return 1

    try:
        pgn_text = pgn_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Could not read PGN file: {exc}", file=sys.stderr)
        return 1

    engine: StockfishEngine | None = None
    try:
        engine = StockfishEngine()
        pipeline = build_default_game_analysis_pipeline(engine)
        result = pipeline.analyze_pgn(pgn_text)
    except StockfishUnavailableError as exc:
        print(f"Stockfish unavailable: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Invalid PGN or analysis input: {exc}", file=sys.stderr)
        return 3
    finally:
        if engine is not None:
            engine.close()

    print(format_result(result))
    return 0


def _format_detected_event(event) -> str:
    return (
        f"- {event.event_type} side={_side(event.side)} move={event.move.uci()} "
        f"squares={_squares(event.squares)} severity={event.severity}"
    )


def _format_verified_event(event: VerifiedEvent) -> str:
    assessment = event.engine_assessment
    return (
        f"- {event.event.event_type} eval_before={_value(assessment.eval_before)} "
        f"eval_after={_value(assessment.eval_after)} "
        f"eval_delta={_value(assessment.eval_delta)} "
        f"event_impact_for_side={_value(assessment.event_impact_for_side)} "
        f"impact_magnitude={_value(assessment.impact_magnitude)} "
        f"candidate_move={_value(assessment.candidate_move_uci)} "
        f"best_move={_move(assessment.best_move)} depth={_value(assessment.depth)}"
    )


def _format_detected_pattern(pattern: DetectedPattern) -> str:
    return (
        f"- {pattern.pattern_type} frequency={pattern.frequency} "
        f"severity={pattern.severity} supporting_events={len(pattern.supporting_events)}"
    )


def _pattern_types(patterns: tuple[DetectedPattern, ...]) -> str:
    if not patterns:
        return "none"

    return ", ".join(pattern.pattern_type for pattern in patterns)


def _side(side: chess.Color) -> str:
    return "white" if side == chess.WHITE else "black"


def _squares(squares: tuple[chess.Square, ...]) -> str:
    if not squares:
        return "none"

    return ", ".join(chess.square_name(square) for square in squares)


def _move(move: chess.Move | None) -> str:
    if move is None:
        return "none"

    return move.uci()


def _value(value: object) -> str:
    if value is None:
        return "none"

    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
