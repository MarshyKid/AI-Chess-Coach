from pathlib import Path
import unittest

import chess

from ai_chess_coach.models import (
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
    WeaknessProfile,
)
from ai_chess_coach.profiling import WeaknessProfileBuilder


def make_pattern(
    pattern_type: str,
    *,
    severity: float = 1.0,
    frequency: int = 1,
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pattern_type,
        frequency=frequency,
        severity=severity,
        supporting_events=(),
    )


def make_verified_event() -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type="hanging_piece_created",
            side=chess.WHITE,
            move=chess.Move.from_uci("e2e4"),
            position=chess.Board(),
            squares=(chess.E4,),
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen=chess.Board().fen(),
                move_uci="e2e4",
                move_san="e4",
                ply=1,
            ),
            evidence={},
            severity=1.0,
        ),
        engine_assessment=EngineAssessment(
            eval_before=None,
            eval_after=None,
            eval_delta=None,
            best_move=None,
            principal_variation=(),
            depth=None,
        ),
    )


class WeaknessProfileBuilderTest(unittest.TestCase):
    def test_build_returns_weakness_profile(self) -> None:
        profile = WeaknessProfileBuilder().build((make_pattern("hanging_piece_created"),))

        self.assertIsInstance(profile, WeaknessProfile)

    def test_recurring_themes_are_sorted_deterministically(self) -> None:
        low_severity = make_pattern("z_low", severity=1.0, frequency=10)
        high_low_frequency = make_pattern("b_high_low_frequency", severity=3.0, frequency=1)
        high_high_frequency_b = make_pattern("b_high_high_frequency", severity=3.0, frequency=2)
        high_high_frequency_a = make_pattern("a_high_high_frequency", severity=3.0, frequency=2)

        profile = WeaknessProfileBuilder().build(
            (
                low_severity,
                high_low_frequency,
                high_high_frequency_b,
                high_high_frequency_a,
            )
        )

        self.assertEqual(
            [pattern.pattern_type for pattern in profile.recurring_themes],
            [
                "a_high_high_frequency",
                "b_high_high_frequency",
                "b_high_low_frequency",
                "z_low",
            ],
        )

    def test_negative_patterns_are_classified_into_weaknesses(self) -> None:
        patterns = (
            make_pattern("hanging_piece_created"),
            make_pattern("hanging_piece_ignored"),
            make_pattern("hanging_piece_lost"),
            make_pattern("fork_missed"),
            make_pattern("fork_allowed"),
            make_pattern("knight_outpost_missed"),
        )

        profile = WeaknessProfileBuilder().build(patterns)

        self.assertEqual(
            {pattern.pattern_type for pattern in profile.weaknesses},
            {pattern.pattern_type for pattern in patterns},
        )

    def test_positive_patterns_are_classified_into_strengths(self) -> None:
        patterns = (
            make_pattern("fork_created"),
            make_pattern("knight_outpost_created"),
        )

        profile = WeaknessProfileBuilder().build(patterns)

        self.assertEqual(
            {pattern.pattern_type for pattern in profile.strengths},
            {pattern.pattern_type for pattern in patterns},
        )

    def test_unknown_patterns_remain_only_in_recurring_themes(self) -> None:
        unknown = make_pattern("time_pressure_pattern")

        profile = WeaknessProfileBuilder().build((unknown,))

        self.assertEqual(profile.recurring_themes, (unknown,))
        self.assertEqual(profile.strengths, ())
        self.assertEqual(profile.weaknesses, ())

    def test_empty_input_returns_empty_profile(self) -> None:
        profile = WeaknessProfileBuilder().build(())

        self.assertEqual(profile.strengths, ())
        self.assertEqual(profile.weaknesses, ())
        self.assertEqual(profile.recurring_themes, ())

    def test_raw_pgn_strings_raise_type_error(self) -> None:
        with self.assertRaises(TypeError):
            WeaknessProfileBuilder().build(("1. e4 e5",))  # type: ignore[arg-type]

    def test_raw_detected_events_raise_type_error(self) -> None:
        event = make_verified_event().event

        with self.assertRaises(TypeError):
            WeaknessProfileBuilder().build((event,))  # type: ignore[arg-type]

    def test_raw_verified_events_raise_type_error(self) -> None:
        event = make_verified_event()

        with self.assertRaises(TypeError):
            WeaknessProfileBuilder().build((event,))  # type: ignore[arg-type]

    def test_builder_does_not_import_stockfish_engine_or_llms(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "profiling"
            / "weakness_profile_builder.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)

    def test_weakness_profile_builder_is_exported_from_profiling_package(self) -> None:
        import ai_chess_coach.profiling as profiling

        self.assertIs(profiling.WeaknessProfileBuilder, WeaknessProfileBuilder)
