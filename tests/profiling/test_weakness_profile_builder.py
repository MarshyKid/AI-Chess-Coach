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
from ai_chess_coach.relevance import CoachingRelevancePolicy


def make_verified_event(
    event_type: str = "hanging_piece_created",
    *,
    event_impact_for_side: int | None = -100,
    impact_magnitude: int | None = 100,
    move_uci: str = "e2e4",
) -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=chess.WHITE,
            move=chess.Move.from_uci(move_uci),
            position=chess.Board(),
            squares=(chess.E4,),
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen=chess.Board().fen(),
                move_uci=move_uci,
                move_san=move_uci,
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
            impact_magnitude=impact_magnitude,
            event_impact_for_side=event_impact_for_side,
        ),
    )


def make_pattern(
    pattern_type: str,
    *,
    severity: float = 1.0,
    frequency: int = 1,
    supporting_events: tuple[VerifiedEvent, ...] | None = None,
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pattern_type,
        frequency=frequency,
        severity=severity,
        supporting_events=supporting_events
        if supporting_events is not None
        else (make_verified_event(pattern_type),),
    )


class WeaknessProfileBuilderTest(unittest.TestCase):
    def test_build_returns_weakness_profile(self) -> None:
        profile = WeaknessProfileBuilder().build((make_pattern("hanging_piece_created"),))

        self.assertIsInstance(profile, WeaknessProfile)

    def test_recurring_themes_are_sorted_deterministically_after_recomputing_profile_patterns(
        self,
    ) -> None:
        low_severity = make_pattern(
            "hanging_piece_created",
            supporting_events=(
                make_verified_event(
                    "hanging_piece_created",
                    event_impact_for_side=-100,
                    impact_magnitude=100,
                ),
            ),
        )
        high_low_frequency = make_pattern(
            "fork_missed",
            supporting_events=(
                make_verified_event(
                    "fork_missed",
                    event_impact_for_side=-300,
                    impact_magnitude=300,
                ),
            ),
        )
        high_high_frequency_b = make_pattern(
            "fork_allowed",
            supporting_events=(
                make_verified_event(
                    "fork_allowed",
                    event_impact_for_side=-300,
                    impact_magnitude=300,
                    move_uci="g1f3",
                ),
                make_verified_event(
                    "fork_allowed",
                    event_impact_for_side=-300,
                    impact_magnitude=300,
                    move_uci="b1c3",
                ),
            ),
        )
        high_high_frequency_a = make_pattern(
            "knight_outpost_missed",
            supporting_events=(
                make_verified_event(
                    "knight_outpost_missed",
                    event_impact_for_side=-300,
                    impact_magnitude=300,
                    move_uci="d2d4",
                ),
                make_verified_event(
                    "knight_outpost_missed",
                    event_impact_for_side=-300,
                    impact_magnitude=300,
                    move_uci="c2c4",
                ),
            ),
        )

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
                "fork_allowed",
                "knight_outpost_missed",
                "fork_missed",
                "hanging_piece_created",
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
            make_pattern(
                "fork_created",
                supporting_events=(
                    make_verified_event(
                        "fork_created",
                        event_impact_for_side=100,
                        impact_magnitude=100,
                    ),
                ),
            ),
            make_pattern(
                "knight_outpost_created",
                supporting_events=(
                    make_verified_event(
                        "knight_outpost_created",
                        event_impact_for_side=100,
                        impact_magnitude=100,
                    ),
                ),
            ),
        )

        profile = WeaknessProfileBuilder().build(patterns)

        self.assertEqual(
            {pattern.pattern_type for pattern in profile.strengths},
            {pattern.pattern_type for pattern in patterns},
        )

    def test_unknown_patterns_are_excluded_from_user_facing_profile_fields(self) -> None:
        unknown = make_pattern(
            "time_pressure_pattern",
            supporting_events=(
                make_verified_event(
                    "time_pressure_pattern",
                    event_impact_for_side=-100,
                    impact_magnitude=100,
                ),
            ),
        )

        profile = WeaknessProfileBuilder().build((unknown,))

        self.assertEqual(profile.recurring_themes, ())
        self.assertEqual(profile.strengths, ())
        self.assertEqual(profile.weaknesses, ())

    def test_low_missing_and_polarity_mismatched_events_are_excluded(self) -> None:
        relevant = make_verified_event(
            "fork_missed",
            event_impact_for_side=-120,
            impact_magnitude=120,
        )
        low_impact = make_verified_event(
            "fork_missed",
            event_impact_for_side=-79,
            impact_magnitude=79,
            move_uci="g1f3",
        )
        missing_impact = make_verified_event(
            "fork_missed",
            event_impact_for_side=None,
            impact_magnitude=None,
            move_uci="b1c3",
        )
        polarity_mismatch = make_verified_event(
            "fork_missed",
            event_impact_for_side=300,
            impact_magnitude=300,
            move_uci="d2d4",
        )
        pattern = make_pattern(
            "fork_missed",
            frequency=4,
            severity=999.0,
            supporting_events=(relevant, low_impact, missing_impact, polarity_mismatch),
        )

        profile = WeaknessProfileBuilder().build((pattern,))

        self.assertEqual(len(profile.weaknesses), 1)
        profile_pattern = profile.weaknesses[0]
        self.assertIsNot(profile_pattern, pattern)
        self.assertEqual(profile_pattern.frequency, 1)
        self.assertEqual(profile_pattern.severity, 120.0)
        self.assertEqual(profile_pattern.supporting_events, (relevant,))
        self.assertEqual(pattern.frequency, 4)
        self.assertEqual(pattern.severity, 999.0)
        self.assertEqual(
            pattern.supporting_events,
            (relevant, low_impact, missing_impact, polarity_mismatch),
        )

    def test_profile_pattern_severity_is_average_filtered_impact_magnitude(self) -> None:
        first = make_verified_event(
            "hanging_piece_created",
            event_impact_for_side=-100,
            impact_magnitude=100,
        )
        second = make_verified_event(
            "hanging_piece_created",
            event_impact_for_side=-300,
            impact_magnitude=300,
            move_uci="g1f3",
        )
        pattern = make_pattern(
            "hanging_piece_created",
            supporting_events=(first, second),
        )

        profile_pattern = WeaknessProfileBuilder().build((pattern,)).weaknesses[0]

        self.assertEqual(profile_pattern.frequency, 2)
        self.assertEqual(profile_pattern.severity, 200.0)

    def test_custom_relevance_policy_is_used(self) -> None:
        event = make_verified_event(
            "hanging_piece_created",
            event_impact_for_side=-90,
            impact_magnitude=90,
        )
        pattern = make_pattern("hanging_piece_created", supporting_events=(event,))

        profile = WeaknessProfileBuilder(
            CoachingRelevancePolicy(min_impact_centipawns=100)
        ).build((pattern,))

        self.assertEqual(profile.weaknesses, ())
        self.assertEqual(profile.recurring_themes, ())

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

    def test_selector_and_profile_builder_share_relevance_behavior(self) -> None:
        from ai_chess_coach.coaching import CoachingMomentSelector

        relevant = make_verified_event(
            "hanging_piece_created",
            event_impact_for_side=-100,
            impact_magnitude=100,
        )
        irrelevant = make_verified_event(
            "hanging_piece_created",
            event_impact_for_side=100,
            impact_magnitude=100,
            move_uci="g1f3",
        )

        selected_events = tuple(
            group.events[0]
            for group in CoachingMomentSelector().select((relevant, irrelevant))
        )
        profile = WeaknessProfileBuilder().build(
            (
                make_pattern(
                    "hanging_piece_created",
                    supporting_events=(relevant, irrelevant),
                ),
            )
        )
        profile_events = profile.weaknesses[0].supporting_events

        self.assertEqual(selected_events, profile_events)

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
        self.assertNotIn("featurestore", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)

    def test_builder_does_not_define_local_positive_or_negative_event_type_sets(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "profiling"
            / "weakness_profile_builder.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("POSITIVE_PATTERN_TYPES", source)
        self.assertNotIn("NEGATIVE_PATTERN_TYPES", source)

    def test_weakness_profile_builder_is_exported_from_profiling_package(self) -> None:
        import ai_chess_coach.profiling as profiling

        self.assertIs(profiling.WeaknessProfileBuilder, WeaknessProfileBuilder)
