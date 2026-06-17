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
from ai_chess_coach.retrieval import EvidenceRetriever


def make_verified_event(
    event_type: str,
    *,
    move_uci: str = "e2e4",
    eval_delta: int | None = None,
    event_severity: float = 1.0,
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


class EvidenceRetrieverTest(unittest.TestCase):
    def test_retrieves_verified_events(self) -> None:
        event = make_verified_event("fork_missed")

        events = EvidenceRetriever().retrieve_events((event,))

        self.assertEqual(events, (event,))

    def test_filters_events_by_event_type(self) -> None:
        first = make_verified_event("fork_missed")
        second = make_verified_event("hanging_piece_created")

        events = EvidenceRetriever().retrieve_events(
            (first, second),
            event_type="hanging_piece_created",
        )

        self.assertEqual(events, (second,))

    def test_ranks_events_by_absolute_eval_delta_when_available(self) -> None:
        low = make_verified_event("fork_missed", eval_delta=25)
        high = make_verified_event("hanging_piece_lost", eval_delta=-100)

        events = EvidenceRetriever().retrieve_events((low, high))

        self.assertEqual(events, (high, low))

    def test_events_fall_back_to_event_severity_when_eval_delta_is_none(self) -> None:
        low = make_verified_event("fork_missed", eval_delta=None, event_severity=0.25)
        high = make_verified_event("fork_allowed", eval_delta=None, event_severity=1.5)

        events = EvidenceRetriever().retrieve_events((low, high))

        self.assertEqual(events, (high, low))

    def test_event_ranking_ties_use_event_type_then_move_uci(self) -> None:
        second = make_verified_event("fork_missed", move_uci="g1f3", eval_delta=50)
        first = make_verified_event("fork_allowed", move_uci="g1h3", eval_delta=-50)

        events = EvidenceRetriever().retrieve_events((second, first))

        self.assertEqual(events, (first, second))

    def test_applies_event_limit(self) -> None:
        high = make_verified_event("hanging_piece_lost", eval_delta=100)
        low = make_verified_event("fork_missed", eval_delta=10)

        events = EvidenceRetriever().retrieve_events((low, high), limit=1)

        self.assertEqual(events, (high,))

    def test_event_limit_zero_returns_empty_tuple(self) -> None:
        event = make_verified_event("fork_missed")

        events = EvidenceRetriever().retrieve_events((event,), limit=0)

        self.assertEqual(events, ())

    def test_retrieves_detected_patterns(self) -> None:
        pattern = make_pattern("fork_missed")

        patterns = EvidenceRetriever().retrieve_patterns((pattern,))

        self.assertEqual(patterns, (pattern,))

    def test_filters_patterns_by_pattern_type(self) -> None:
        first = make_pattern("fork_missed")
        second = make_pattern("hanging_piece_created")

        patterns = EvidenceRetriever().retrieve_patterns(
            (first, second),
            pattern_type="hanging_piece_created",
        )

        self.assertEqual(patterns, (second,))

    def test_ranks_patterns_by_severity_frequency_and_pattern_type(self) -> None:
        low_severity = make_pattern("z_low", severity=1.0, frequency=100)
        high_low_frequency = make_pattern("b_high_low_frequency", severity=3.0, frequency=1)
        high_high_frequency_b = make_pattern("b_high_high_frequency", severity=3.0, frequency=2)
        high_high_frequency_a = make_pattern("a_high_high_frequency", severity=3.0, frequency=2)

        patterns = EvidenceRetriever().retrieve_patterns(
            (
                low_severity,
                high_low_frequency,
                high_high_frequency_b,
                high_high_frequency_a,
            )
        )

        self.assertEqual(
            [pattern.pattern_type for pattern in patterns],
            [
                "a_high_high_frequency",
                "b_high_high_frequency",
                "b_high_low_frequency",
                "z_low",
            ],
        )

    def test_applies_pattern_limit(self) -> None:
        high = make_pattern("high", severity=10.0)
        low = make_pattern("low", severity=1.0)

        patterns = EvidenceRetriever().retrieve_patterns((low, high), limit=1)

        self.assertEqual(patterns, (high,))

    def test_retrieves_profile_data_from_all_sections(self) -> None:
        strength = make_pattern("fork_created", severity=3.0)
        execution_strength = make_pattern("knight_outpost_created", severity=2.5)
        weakness = make_pattern("fork_missed", severity=2.0)
        theme = make_pattern("neutral_theme", severity=1.0)
        profile = WeaknessProfile(
            strengths=(strength,),
            execution_strengths=(execution_strength,),
            weaknesses=(weakness,),
            recurring_themes=(theme,),
        )

        patterns = EvidenceRetriever().retrieve_profile(profile)

        self.assertEqual(patterns, (strength, execution_strength, weakness, theme))

    def test_profile_retrieval_respects_include_flags(self) -> None:
        strength = make_pattern("fork_created", severity=3.0)
        execution_strength = make_pattern("knight_outpost_created", severity=2.5)
        weakness = make_pattern("fork_missed", severity=2.0)
        theme = make_pattern("neutral_theme", severity=1.0)
        profile = WeaknessProfile(
            strengths=(strength,),
            execution_strengths=(execution_strength,),
            weaknesses=(weakness,),
            recurring_themes=(theme,),
        )

        patterns = EvidenceRetriever().retrieve_profile(
            profile,
            include_strengths=False,
            include_execution_strengths=False,
            include_recurring_themes=False,
        )

        self.assertEqual(patterns, (weakness,))

    def test_profile_retrieval_can_include_only_execution_strengths(self) -> None:
        strength = make_pattern("fork_created", severity=3.0)
        execution_strength = make_pattern("knight_outpost_created", severity=2.5)
        weakness = make_pattern("fork_missed", severity=2.0)
        profile = WeaknessProfile(
            strengths=(strength,),
            execution_strengths=(execution_strength,),
            weaknesses=(weakness,),
            recurring_themes=(),
        )

        patterns = EvidenceRetriever().retrieve_profile(
            profile,
            include_strengths=False,
            include_weaknesses=False,
            include_recurring_themes=False,
        )

        self.assertEqual(patterns, (execution_strength,))

    def test_profile_retrieval_deduplicates_pattern_objects(self) -> None:
        shared = make_pattern("fork_missed", severity=2.0)
        other = make_pattern("fork_allowed", severity=1.0)
        profile = WeaknessProfile(
            strengths=(),
            weaknesses=(shared,),
            recurring_themes=(shared, other),
        )

        patterns = EvidenceRetriever().retrieve_profile(profile)

        self.assertEqual(patterns, (shared, other))

    def test_profile_retrieval_applies_limit(self) -> None:
        high = make_pattern("high", severity=10.0)
        low = make_pattern("low", severity=1.0)
        profile = WeaknessProfile(
            strengths=(),
            weaknesses=(),
            recurring_themes=(low, high),
        )

        patterns = EvidenceRetriever().retrieve_profile(profile, limit=1)

        self.assertEqual(patterns, (high,))

    def test_rejects_raw_pgn_strings_and_wrong_object_types(self) -> None:
        event = make_verified_event("fork_missed")
        pattern = make_pattern("fork_missed")

        with self.assertRaises(TypeError):
            EvidenceRetriever().retrieve_events(("1. e4 e5",))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            EvidenceRetriever().retrieve_events((event.event,))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            EvidenceRetriever().retrieve_events((pattern,))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            EvidenceRetriever().retrieve_patterns(("1. e4 e5",))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            EvidenceRetriever().retrieve_patterns((event,))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            EvidenceRetriever().retrieve_profile(pattern)  # type: ignore[arg-type]

    def test_rejects_negative_limits(self) -> None:
        retriever = EvidenceRetriever()

        with self.assertRaises(ValueError):
            retriever.retrieve_events((), limit=-1)
        with self.assertRaises(ValueError):
            retriever.retrieve_patterns((), limit=-1)
        with self.assertRaises(ValueError):
            retriever.retrieve_profile(
                WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=()),
                limit=-1,
            )

    def test_retriever_does_not_import_engine_llms_or_direct_chess_analysis(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "retrieval"
            / "evidence_retriever.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)

    def test_evidence_retriever_is_exported_from_retrieval_package(self) -> None:
        import ai_chess_coach.retrieval as retrieval

        self.assertIs(retrieval.EvidenceRetriever, EvidenceRetriever)
