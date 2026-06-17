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
    impact_magnitude: int | None = None,
    event_score_kind: str = "centipawn",
    impact_rank: int | None = None,
    ply: int = 1,
    squares: tuple[chess.Square, ...] = (chess.E4,),
    event_severity: float = 1.0,
) -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=chess.WHITE,
            move=chess.Move.from_uci(move_uci),
            position=chess.Board(),
            squares=squares,
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen=chess.Board().fen(),
                move_uci=move_uci,
                move_san=move_uci,
                ply=ply,
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
            impact_magnitude=impact_magnitude,
            event_score_kind=event_score_kind,  # type: ignore[arg-type]
            impact_rank=impact_rank,
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

    def test_ranks_centipawn_events_by_impact_magnitude(self) -> None:
        low = make_verified_event("fork_missed", impact_magnitude=25)
        high = make_verified_event("hanging_piece_lost", impact_magnitude=100)

        events = EvidenceRetriever().retrieve_events((low, high))

        self.assertEqual(events, (high, low))

    def test_candidate_aware_impact_magnitude_outranks_raw_eval_delta(self) -> None:
        canonical_high = make_verified_event(
            "fork_missed",
            eval_delta=10,
            impact_magnitude=300,
        )
        raw_high = make_verified_event(
            "hanging_piece_created",
            move_uci="g1f3",
            eval_delta=900,
            impact_magnitude=50,
        )

        events = EvidenceRetriever().retrieve_events((raw_high, canonical_high))

        self.assertEqual(events, (canonical_high, raw_high))

    def test_raw_eval_delta_without_canonical_impact_falls_back_to_severity(self) -> None:
        canonical = make_verified_event(
            "fork_missed",
            eval_delta=10,
            impact_magnitude=80,
        )
        raw_large = make_verified_event(
            "hanging_piece_created",
            move_uci="g1f3",
            eval_delta=10_000,
            impact_magnitude=None,
            event_severity=0.5,
        )

        events = EvidenceRetriever().retrieve_events((raw_large, canonical))

        self.assertEqual(events, (canonical, raw_large))

    def test_mate_events_with_impact_rank_sort_before_centipawn_events(self) -> None:
        mate = make_verified_event(
            "fork_allowed",
            event_score_kind="mate",
            impact_rank=100,
            event_severity=0.1,
        )
        centipawn = make_verified_event(
            "hanging_piece_lost",
            move_uci="g1f3",
            impact_magnitude=10_000,
        )

        events = EvidenceRetriever().retrieve_events((centipawn, mate))

        self.assertEqual(events, (mate, centipawn))

    def test_mate_events_use_impact_rank_not_detector_severity(self) -> None:
        low_rank_high_severity = make_verified_event(
            "fork_allowed",
            event_score_kind="mate",
            impact_rank=100,
            event_severity=10_000.0,
        )
        high_rank_low_severity = make_verified_event(
            "fork_missed",
            move_uci="g1f3",
            event_score_kind="mate",
            impact_rank=300,
            event_severity=0.1,
        )

        events = EvidenceRetriever().retrieve_events(
            (low_rank_high_severity, high_rank_low_severity)
        )

        self.assertEqual(events, (high_rank_low_severity, low_rank_high_severity))

    def test_mate_event_missing_impact_rank_falls_back_to_event_severity(self) -> None:
        high_severity = make_verified_event(
            "fork_allowed",
            event_score_kind="mate",
            impact_rank=None,
            event_severity=1.5,
        )
        low_severity = make_verified_event(
            "fork_missed",
            move_uci="g1f3",
            event_score_kind="mate",
            impact_rank=None,
            event_severity=0.25,
        )

        events = EvidenceRetriever().retrieve_events((low_severity, high_severity))

        self.assertEqual(events, (high_severity, low_severity))

    def test_events_fall_back_to_event_severity_when_canonical_impact_is_unavailable(
        self,
    ) -> None:
        low = make_verified_event("fork_missed", event_severity=0.25)
        high = make_verified_event("fork_allowed", move_uci="g1f3", event_severity=1.5)

        events = EvidenceRetriever().retrieve_events((low, high))

        self.assertEqual(events, (high, low))

    def test_event_ranking_ties_use_ply_event_type_move_uci_and_squares(self) -> None:
        later_ply = make_verified_event(
            "fork_allowed",
            move_uci="g1f3",
            impact_magnitude=50,
            ply=2,
            squares=(chess.F3,),
        )
        earlier_type = make_verified_event(
            "fork_allowed",
            move_uci="g1h3",
            impact_magnitude=50,
            ply=1,
            squares=(chess.H3,),
        )
        later_type = make_verified_event(
            "fork_missed",
            move_uci="a2a3",
            impact_magnitude=50,
            ply=1,
            squares=(chess.A3,),
        )
        earlier_move = make_verified_event(
            "fork_allowed",
            move_uci="b1c3",
            impact_magnitude=50,
            ply=1,
            squares=(chess.C3,),
        )
        earlier_square = make_verified_event(
            "fork_allowed",
            move_uci="b1c3",
            impact_magnitude=50,
            ply=1,
            squares=(chess.A1,),
        )

        events = EvidenceRetriever().retrieve_events(
            (later_ply, later_type, earlier_type, earlier_move, earlier_square)
        )

        self.assertEqual(
            events,
            (earlier_square, earlier_move, earlier_type, later_type, later_ply),
        )

    def test_applies_event_limit(self) -> None:
        high = make_verified_event("hanging_piece_lost", impact_magnitude=100)
        low = make_verified_event("fork_missed", impact_magnitude=10)

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
        self.assertNotIn("ai_chess_coach.detectors", source)
        self.assertNotIn("featurestore", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("httpx", source)

    def test_evidence_retriever_is_exported_from_retrieval_package(self) -> None:
        import ai_chess_coach.retrieval as retrieval

        self.assertIs(retrieval.EvidenceRetriever, EvidenceRetriever)
