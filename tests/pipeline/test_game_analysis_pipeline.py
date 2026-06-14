"""Tests for the end-to-end game analysis pipeline."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

import chess

from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    EventMetadata,
    GameAnalysisResult,
    VerifiedEvent,
    WeaknessProfile,
)
from ai_chess_coach.pipeline import GameAnalysisPipeline


SIMPLE_PGN = """
[Event "Task 21 Test"]
[Site "?"]
[Date "2026.06.14"]
[Round "-"]
[White "White"]
[Black "Black"]
[Result "*"]

1. e4 e5 *
"""


class FakeDetectionPipeline:
    def __init__(self) -> None:
        self.transitions = []

    def run(self, transition):
        self.transitions.append(transition)
        if transition.ply == 1:
            return [_event_from_transition(transition, "hanging_piece_created", 1.0)]
        if transition.ply == 2:
            return [
                _event_from_transition(transition, "fork_created", 2.0),
                _event_from_transition(transition, "fork_missed", 3.0),
            ]

        return []


class EmptyDetectionPipeline:
    def __init__(self) -> None:
        self.transitions = []

    def run(self, transition):
        self.transitions.append(transition)
        return []


class FakeEventVerifier:
    def __init__(self) -> None:
        self.events = []

    def verify(self, event: DetectedEvent) -> VerifiedEvent:
        self.events.append(event)
        return VerifiedEvent(
            event=event,
            engine_assessment=EngineAssessment(
                eval_before=0,
                eval_after=100,
                eval_delta=100,
                best_move=event.move,
                principal_variation=(event.move,),
                depth=1,
            ),
        )


class RaisingEventVerifier:
    def verify(self, event: DetectedEvent) -> VerifiedEvent:
        raise RuntimeError("verification failed")


class FakePatternAggregator:
    def __init__(self, patterns: tuple[DetectedPattern, ...] = ()) -> None:
        self.received_events = None
        self._patterns = patterns

    def aggregate(self, events):
        self.received_events = tuple(events)
        return self._patterns


class FakeWeaknessProfileBuilder:
    def __init__(self, profile: WeaknessProfile | None = None) -> None:
        self.received_patterns = None
        self._profile = profile or WeaknessProfile(
            strengths=(),
            weaknesses=(),
            recurring_themes=(),
        )

    def build(self, patterns):
        self.received_patterns = tuple(patterns)
        return self._profile


class FakeReviewGenerator:
    def __init__(self, moments: tuple[CoachingMoment, ...] = ()) -> None:
        self.received_events = None
        self._moments = moments

    def generate(self, events):
        self.received_events = tuple(events)
        return self._moments


class GameAnalysisResultTest(unittest.TestCase):
    def test_constructs_with_all_fields(self) -> None:
        profile = WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=())
        result = GameAnalysisResult(
            transitions=(),
            detected_events=(),
            verified_events=(),
            detected_patterns=(),
            weakness_profile=profile,
            coaching_moments=(),
        )

        self.assertEqual((), result.transitions)
        self.assertIs(profile, result.weakness_profile)

    def test_is_frozen(self) -> None:
        result = GameAnalysisResult(
            transitions=(),
            detected_events=(),
            verified_events=(),
            detected_patterns=(),
            weakness_profile=WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=()),
            coaching_moments=(),
        )

        with self.assertRaises(FrozenInstanceError):
            result.transitions = ()  # type: ignore[misc]

    def test_is_exported_from_models_package(self) -> None:
        from ai_chess_coach.models import GameAnalysisResult as ExportedGameAnalysisResult

        self.assertIs(GameAnalysisResult, ExportedGameAnalysisResult)


class GameAnalysisPipelineTest(unittest.TestCase):
    def test_is_exported_from_pipeline_package(self) -> None:
        from ai_chess_coach.pipeline import GameAnalysisPipeline as ExportedGameAnalysisPipeline

        self.assertIs(GameAnalysisPipeline, ExportedGameAnalysisPipeline)

    def test_analyze_pgn_orchestrates_all_steps(self) -> None:
        pattern = DetectedPattern(
            pattern_type="hanging_piece_created",
            frequency=1,
            severity=100.0,
            supporting_events=(),
        )
        moment = CoachingMoment(
            title="Hanging Piece Created",
            explanation="A verified event was found.",
            supporting_evidence=(),
            position_reference="after-fen",
            highlights=(),
        )
        profile = WeaknessProfile(
            strengths=(),
            weaknesses=(pattern,),
            recurring_themes=(pattern,),
        )
        detection_pipeline = FakeDetectionPipeline()
        verifier = FakeEventVerifier()
        aggregator = FakePatternAggregator(patterns=(pattern,))
        builder = FakeWeaknessProfileBuilder(profile=profile)
        review_generator = FakeReviewGenerator(moments=(moment,))

        result = GameAnalysisPipeline(
            detection_pipeline=detection_pipeline,  # type: ignore[arg-type]
            event_verifier=verifier,  # type: ignore[arg-type]
            pattern_aggregator=aggregator,  # type: ignore[arg-type]
            weakness_profile_builder=builder,  # type: ignore[arg-type]
            review_generator=review_generator,  # type: ignore[arg-type]
        ).analyze_pgn(SIMPLE_PGN)

        self.assertIsInstance(result, GameAnalysisResult)
        self.assertEqual(2, len(result.transitions))
        self.assertEqual(result.transitions, tuple(detection_pipeline.transitions))
        self.assertEqual(
            ("hanging_piece_created", "fork_created", "fork_missed"),
            tuple(event.event_type for event in result.detected_events),
        )
        self.assertEqual(result.detected_events, tuple(verifier.events))
        self.assertEqual(result.verified_events, aggregator.received_events)
        self.assertEqual(result.detected_patterns, builder.received_patterns)
        self.assertEqual(result.verified_events, review_generator.received_events)
        self.assertEqual((pattern,), result.detected_patterns)
        self.assertIs(profile, result.weakness_profile)
        self.assertEqual((moment,), result.coaching_moments)

    def test_no_event_game_returns_empty_downstream_outputs(self) -> None:
        detection_pipeline = EmptyDetectionPipeline()
        verifier = FakeEventVerifier()
        aggregator = FakePatternAggregator()
        builder = FakeWeaknessProfileBuilder()
        review_generator = FakeReviewGenerator()

        result = GameAnalysisPipeline(
            detection_pipeline=detection_pipeline,  # type: ignore[arg-type]
            event_verifier=verifier,  # type: ignore[arg-type]
            pattern_aggregator=aggregator,  # type: ignore[arg-type]
            weakness_profile_builder=builder,  # type: ignore[arg-type]
            review_generator=review_generator,  # type: ignore[arg-type]
        ).analyze_pgn(SIMPLE_PGN)

        self.assertEqual(2, len(result.transitions))
        self.assertEqual((), result.detected_events)
        self.assertEqual((), result.verified_events)
        self.assertEqual((), result.detected_patterns)
        self.assertEqual((), result.coaching_moments)
        self.assertEqual(WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=()), result.weakness_profile)
        self.assertEqual((), aggregator.received_events)
        self.assertEqual((), builder.received_patterns)
        self.assertEqual((), review_generator.received_events)

    def test_verifier_exception_propagates(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "verification failed"):
            GameAnalysisPipeline(
                detection_pipeline=FakeDetectionPipeline(),  # type: ignore[arg-type]
                event_verifier=RaisingEventVerifier(),  # type: ignore[arg-type]
            ).analyze_pgn(SIMPLE_PGN)

    def test_invalid_pgn_propagates_replay_error(self) -> None:
        with self.assertRaises(ValueError):
            GameAnalysisPipeline(
                detection_pipeline=FakeDetectionPipeline(),  # type: ignore[arg-type]
                event_verifier=FakeEventVerifier(),  # type: ignore[arg-type]
            ).analyze_pgn("   ")

    def test_pipeline_source_respects_architecture_boundaries(self) -> None:
        source = Path("src/ai_chess_coach/pipeline/game_analysis_pipeline.py").read_text()
        lower_source = source.lower()

        self.assertNotIn("openai", lower_source)
        self.assertNotIn("llm", lower_source)
        self.assertNotIn("stockfishengine", lower_source)
        self.assertNotIn("chess.engine", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("attackers", lower_source)


def _event_from_transition(transition, event_type: str, severity: float) -> DetectedEvent:
    return DetectedEvent(
        event_type=event_type,
        side=chess.WHITE,
        move=transition.move,
        position=transition.after_position,
        squares=(transition.move.to_square,),
        metadata=EventMetadata(
            before_fen=transition.before_position.fen(),
            after_fen=transition.after_position.fen(),
            move_uci=transition.move.uci(),
            move_san=transition.san,
            ply=transition.ply,
        ),
        evidence={},
        severity=severity,
    )
