from pathlib import Path
import unittest

import chess

from ai_chess_coach.models import (
    DetectedEvent,
    EngineAssessment,
    VerifiedEvent,
)
from ai_chess_coach.profiling import PatternAggregator


def make_verified_event(
    event_type: str,
    *,
    event_severity: float = 1.0,
    eval_delta: int | None = None,
) -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=chess.WHITE,
            move=chess.Move.from_uci("e2e4"),
            position=chess.Board(),
            squares=(chess.E4,),
            evidence={},
            severity=event_severity,
        ),
        engine_assessment=EngineAssessment(
            eval_before=None,
            eval_after=None,
            eval_delta=eval_delta,
            best_move=None,
            principal_variation=(),
            depth=None,
        ),
    )


class PatternAggregatorTest(unittest.TestCase):
    def test_groups_verified_events_by_event_type(self) -> None:
        first = make_verified_event("fork_missed", eval_delta=20)
        second = make_verified_event("hanging_piece_created", eval_delta=50)
        third = make_verified_event("fork_missed", eval_delta=40)

        patterns = PatternAggregator().aggregate((first, second, third))

        self.assertEqual(
            [pattern.pattern_type for pattern in patterns],
            ["fork_missed", "hanging_piece_created"],
        )

    def test_counts_frequency_per_group(self) -> None:
        first = make_verified_event("fork_missed", eval_delta=20)
        second = make_verified_event("fork_missed", eval_delta=40)

        pattern = PatternAggregator().aggregate((first, second))[0]

        self.assertEqual(pattern.frequency, 2)

    def test_supporting_events_are_tuple_and_preserve_group_input_order(self) -> None:
        first = make_verified_event("fork_missed", eval_delta=20)
        second = make_verified_event("fork_missed", eval_delta=40)

        pattern = PatternAggregator().aggregate((first, second))[0]

        self.assertEqual(pattern.supporting_events, (first, second))

    def test_severity_uses_average_absolute_eval_delta_when_available(self) -> None:
        first = make_verified_event("hanging_piece_created", eval_delta=-100)
        second = make_verified_event("hanging_piece_created", eval_delta=50)

        pattern = PatternAggregator().aggregate((first, second))[0]

        self.assertEqual(pattern.severity, 75.0)

    def test_severity_falls_back_to_event_severity_when_eval_delta_unavailable(self) -> None:
        first = make_verified_event("fork_allowed", event_severity=0.5, eval_delta=None)
        second = make_verified_event("fork_allowed", event_severity=1.5, eval_delta=None)

        pattern = PatternAggregator().aggregate((first, second))[0]

        self.assertEqual(pattern.severity, 1.0)

    def test_mixed_group_ignores_none_eval_delta_when_concrete_delta_exists(self) -> None:
        first = make_verified_event("fork_allowed", event_severity=100.0, eval_delta=None)
        second = make_verified_event("fork_allowed", event_severity=1.0, eval_delta=-25)
        third = make_verified_event("fork_allowed", event_severity=1.0, eval_delta=75)

        pattern = PatternAggregator().aggregate((first, second, third))[0]

        self.assertEqual(pattern.severity, 50.0)

    def test_empty_input_returns_empty_tuple(self) -> None:
        patterns = PatternAggregator().aggregate(())

        self.assertEqual(patterns, ())

    def test_raw_pgn_strings_raise_type_error(self) -> None:
        with self.assertRaises(TypeError):
            PatternAggregator().aggregate(("1. e4 e5",))  # type: ignore[arg-type]

    def test_raw_detected_events_raise_type_error(self) -> None:
        event = make_verified_event("fork_missed").event

        with self.assertRaises(TypeError):
            PatternAggregator().aggregate((event,))  # type: ignore[arg-type]

    def test_aggregator_does_not_import_stockfish_engine_or_llms(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "profiling"
            / "pattern_aggregator.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)

    def test_pattern_aggregator_is_exported_from_profiling_package(self) -> None:
        import ai_chess_coach.profiling as profiling

        self.assertIs(profiling.PatternAggregator, PatternAggregator)
