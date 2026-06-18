"""Golden PGN regression tests for the backend MVP pipeline."""

from __future__ import annotations

from pathlib import Path
import unittest

import chess

from ai_chess_coach.analysis.replay import replay_pgn_string
from ai_chess_coach.coaching import LLMChatCoach, LLMPrompt, ReviewGenerator
from ai_chess_coach.detectors import (
    DetectionPipeline,
    DetectorRegistry,
    ForkDetector,
    HangingPieceDetector,
    KnightOutpostDetector,
)
from ai_chess_coach.models import (
    EngineAssessment,
    EngineScore,
    VerifiedEvent,
    get_event_type_metadata,
)
from ai_chess_coach.pipeline import GameAnalysisPipeline


FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "pgns"


class GoldenFakeVerifier:
    """Deterministic verifier for golden tests that never starts Stockfish."""

    def __init__(self) -> None:
        self.events = []

    def verify(self, event) -> VerifiedEvent:
        self.events.append(event)
        event_type_metadata = get_event_type_metadata(event.event_type)
        event_impact = _fake_event_impact(event.event_type)

        if event_impact is None:
            return VerifiedEvent(
                event=event,
                engine_assessment=EngineAssessment(
                    eval_before=None,
                    eval_after=None,
                    eval_delta=None,
                    best_move=None,
                    principal_variation=(),
                    depth=1,
                ),
            )

        return VerifiedEvent(
            event=event,
            engine_assessment=EngineAssessment(
                eval_before=0,
                eval_after=event_impact,
                eval_delta=event_impact,
                best_move=None,
                principal_variation=(),
                depth=1,
                eval_delta_for_event_side=event_impact,
                impact_magnitude=abs(event_impact),
                candidate_eval_after=(200 if event.candidate_move is not None else None),
                candidate_move_uci=(
                    event.candidate_move.move_uci
                    if event.candidate_move is not None
                    else None
                ),
                event_impact_for_side=event_impact,
                score_before=EngineScore(centipawns=0),
                score_after=EngineScore(centipawns=event_impact),
                candidate_score_after=(
                    EngineScore(centipawns=200)
                    if event.candidate_move is not None
                    else None
                ),
                event_score_kind="centipawn",
                event_impact_rank_for_side=event_impact,
                impact_rank=abs(event_impact),
            ),
        )


class RecordingLLMClient:
    def __init__(self) -> None:
        self.received_prompt: LLMPrompt | None = None

    def generate(self, prompt: LLMPrompt) -> str:
        self.received_prompt = prompt
        return "grounded golden response"


class GoldenPgnRegressionTest(unittest.TestCase):
    def test_hanging_piece_fixture_flows_through_full_backend_pipeline(self) -> None:
        result = _analyze_fixture("hanging_piece_game.pgn")

        self.assertGreaterEqual(len(result.transitions), 1)
        self.assertTrue(
            any(event.event_type.startswith("hanging_piece_") for event in result.detected_events)
        )
        self.assertEqual(len(result.detected_events), len(result.verified_events))
        self.assertTrue(result.detected_patterns)
        self.assertTrue(
            any(
                pattern.pattern_type.startswith("hanging_piece_")
                for pattern in result.weakness_profile.weaknesses
            )
        )
        self.assertTrue(result.coaching_moments)
        self.assertLessEqual(len(result.coaching_moments), len(result.verified_events))
        self.assertTrue(
            all(
                isinstance(evidence, VerifiedEvent)
                for moment in result.coaching_moments
                for evidence in moment.supporting_evidence
            )
        )

    def test_fork_fixture_preserves_candidate_aware_events(self) -> None:
        result = _analyze_fixture("fork_game.pgn")
        fork_missed_events = [
            event for event in result.detected_events if event.event_type == "fork_missed"
        ]

        self.assertTrue(fork_missed_events)
        self.assertTrue(all(event.candidate_move is not None for event in fork_missed_events))
        self.assertTrue(
            any(event.event.event_type == "fork_missed" for event in result.verified_events)
        )
        fork_missed_moments = [
            moment
            for moment in result.coaching_moments
            for evidence in moment.supporting_evidence
            if isinstance(evidence, VerifiedEvent)
            and evidence.event.event_type == "fork_missed"
        ]
        self.assertTrue(fork_missed_moments)
        self.assertEqual(
            fork_missed_events[0].metadata.before_fen,
            fork_missed_moments[0].position_reference,
        )

    def test_outpost_fixture_surfaces_low_impact_execution_strength(self) -> None:
        result = _analyze_fixture("outpost_game.pgn")

        self.assertTrue(
            any(event.event_type == "knight_outpost_created" for event in result.detected_events)
        )
        self.assertTrue(
            any(
                pattern.pattern_type == "knight_outpost_created"
                for pattern in result.detected_patterns
            )
        )
        self.assertFalse(
            any(
                pattern.pattern_type == "knight_outpost_created"
                for pattern in result.weakness_profile.strengths
            )
        )
        self.assertTrue(
            any(
                pattern.pattern_type == "knight_outpost_created"
                for pattern in result.weakness_profile.execution_strengths
            )
        )
        self.assertFalse(
            any(
                evidence.event.event_type == "knight_outpost_created"
                for moment in result.coaching_moments
                for evidence in moment.supporting_evidence
                if isinstance(evidence, VerifiedEvent)
            )
        )

    def test_golden_corpus_keeps_raw_events_separate_from_selected_moments(self) -> None:
        results = tuple(
            _analyze_fixture(fixture_name)
            for fixture_name in (
                "hanging_piece_game.pgn",
                "fork_game.pgn",
                "outpost_game.pgn",
            )
        )
        verified_events = tuple(
            event for result in results for event in result.verified_events
        )
        selected_moments = ReviewGenerator().generate(verified_events)

        self.assertGreater(len(verified_events), len(selected_moments))
        self.assertTrue(selected_moments)
        self.assertTrue(
            all(
                isinstance(evidence, VerifiedEvent)
                for moment in selected_moments
                for evidence in moment.supporting_evidence
            )
        )

    def test_llm_prompt_flow_uses_selected_coaching_moments_as_primary_evidence(self) -> None:
        result = _analyze_fixture("fork_game.pgn")
        client = RecordingLLMClient()

        response = LLMChatCoach(client=client).respond(
            "What should I study from this game?",
            coaching_moments=result.coaching_moments,
            weakness_profile=result.weakness_profile,
        )

        self.assertEqual("grounded golden response", response)
        self.assertIsNotNone(client.received_prompt)
        assert client.received_prompt is not None
        self.assertIn("## Coaching Moments", client.received_prompt.user)
        self.assertIn("## Weakness Profile", client.received_prompt.user)
        self.assertIn("What should I study from this game?", client.received_prompt.user)
        self.assertIn("## Retrieved Verified Events\nNone supplied.", client.received_prompt.user)
        self.assertIn("Use only the supplied structured evidence.", client.received_prompt.system)
        self.assertIn("Do not analyze raw PGNs.", client.received_prompt.system)
        self.assertNotIn("[Event", client.received_prompt.user)

    def test_detectors_remain_engine_free_and_llm_free(self) -> None:
        detector_dir = Path(__file__).parents[2] / "src" / "ai_chess_coach" / "detectors"

        for detector_path in detector_dir.glob("*_detector.py"):
            source = detector_path.read_text(encoding="utf-8").lower()
            with self.subTest(detector=detector_path.name):
                self.assertNotIn("stockfish", source)
                self.assertNotIn("ai_chess_coach.engine", source)
                self.assertNotIn("openai", source)
                self.assertNotIn("anthropic", source)
                self.assertNotIn("gemini", source)
                self.assertNotIn("llm", source)


def _fake_event_impact(event_type: str) -> int | None:
    event_type_metadata = get_event_type_metadata(event_type)
    if event_type_metadata.polarity == "negative":
        return -200
    if event_type_metadata.is_execution_strength:
        return 20
    if event_type_metadata.polarity == "positive":
        return 200

    return None


def _analyze_fixture(fixture_name: str):
    return _pipeline().analyze_pgn(_fixture_text(fixture_name))


def _pipeline() -> GameAnalysisPipeline:
    verifier = GoldenFakeVerifier()
    return GameAnalysisPipeline(
        detection_pipeline=_detection_pipeline(),
        event_verifier=verifier,  # type: ignore[arg-type]
    )


def _detection_pipeline() -> DetectionPipeline:
    registry = DetectorRegistry()
    registry.register(HangingPieceDetector())
    registry.register(ForkDetector())
    registry.register(KnightOutpostDetector())
    return DetectionPipeline(registry)


def _fixture_text(fixture_name: str) -> str:
    return (FIXTURE_DIR / fixture_name).read_text(encoding="utf-8")


class GoldenPgnFixtureTest(unittest.TestCase):
    def test_all_golden_pgn_fixtures_replay(self) -> None:
        for fixture_name in (
            "hanging_piece_game.pgn",
            "fork_game.pgn",
            "outpost_game.pgn",
        ):
            with self.subTest(fixture=fixture_name):
                transitions = replay_pgn_string(_fixture_text(fixture_name))

                self.assertGreaterEqual(len(transitions), 1)
                self.assertTrue(all(transition.san for transition in transitions))
                self.assertTrue(
                    all(isinstance(transition.move, chess.Move) for transition in transitions)
                )
