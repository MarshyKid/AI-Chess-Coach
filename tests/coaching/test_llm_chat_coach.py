from pathlib import Path
import unittest

import chess

from ai_chess_coach.coaching import LLMChatCoach, LLMPrompt, PromptBuilder
from ai_chess_coach.models import (
    CandidateMove,
    CoachingMoment,
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    EngineScore,
    EventMetadata,
    VerifiedEvent,
    WeaknessProfile,
)


class RecordingLLMClient:
    def __init__(self, response: str = "grounded response") -> None:
        self.response = response
        self.received_prompt: LLMPrompt | None = None

    def generate(self, prompt: LLMPrompt) -> str:
        self.received_prompt = prompt
        return self.response


class FailingLLMClient:
    def generate(self, prompt: LLMPrompt) -> str:
        raise RuntimeError("provider failed")


class RecordingPromptBuilder(PromptBuilder):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def build(
        self,
        question: str,
        *,
        coaching_moments=(),
        verified_events=(),
        patterns=(),
        weakness_profile=None,
    ) -> LLMPrompt:
        self.calls.append(
            {
                "question": question,
                "coaching_moments": coaching_moments,
                "verified_events": verified_events,
                "patterns": patterns,
                "weakness_profile": weakness_profile,
            }
        )
        return LLMPrompt(system="custom system", user="custom user")


def make_verified_event(
    event_type: str = "fork_missed",
    *,
    move_uci: str = "a2a3",
    move_san: str = "a3",
    evidence: dict[str, object] | None = None,
    candidate_move: CandidateMove | None = None,
    event_score_kind: str = "centipawn",
    impact_magnitude: int | None = 120,
    impact_rank: int | None = None,
    candidate_score_after: EngineScore | None = None,
) -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=chess.WHITE,
            move=chess.Move.from_uci(move_uci),
            position=chess.Board(),
            squares=(chess.F7,),
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen="after-fen",
                move_uci=move_uci,
                move_san=move_san,
                ply=3,
            ),
            evidence=evidence or {},
            severity=1.0,
            candidate_move=candidate_move,
        ),
        engine_assessment=EngineAssessment(
            eval_before=0,
            eval_after=impact_magnitude,
            eval_delta=impact_magnitude,
            best_move=None,
            principal_variation=(),
            depth=10,
            impact_magnitude=impact_magnitude,
            candidate_move_uci=(
                candidate_move.move_uci if candidate_move is not None else None
            ),
            event_impact_for_side=impact_magnitude,
            candidate_score_after=candidate_score_after,
            event_score_kind=event_score_kind,  # type: ignore[arg-type]
            event_impact_rank_for_side=impact_rank,
            impact_rank=impact_rank,
        ),
    )


def make_pattern(
    pattern_type: str,
    *,
    frequency: int = 2,
    severity: float = 100.0,
    supporting_events: tuple[VerifiedEvent, ...] = (),
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pattern_type,
        frequency=frequency,
        severity=severity,
        supporting_events=supporting_events,
    )


def make_moment(event: VerifiedEvent) -> CoachingMoment:
    return CoachingMoment(
        title="Move 2: Fork missed",
        explanation="The candidate tactic was stronger than the played move.",
        supporting_evidence=(event,),
        position_reference="before-fen",
        highlights=(chess.F7,),
    )


class LLMChatCoachTest(unittest.TestCase):
    def test_respond_builds_prompt_sends_it_to_client_and_returns_response(self) -> None:
        event = make_verified_event(
            evidence={
                "forking_piece_square": "f7",
                "target_squares": ("e5", "h8"),
                "target_pieces": ("k", "r"),
                "forking_move_san": "Nf7+",
            }
        )
        moment = make_moment(event)
        client = RecordingLLMClient(response="coach answer")

        response = LLMChatCoach(client=client).respond(
            "How do I improve forks?",
            coaching_moments=(moment,),
        )

        self.assertEqual(response, "coach answer")
        self.assertIsInstance(client.received_prompt, LLMPrompt)
        assert client.received_prompt is not None
        self.assertIn("How do I improve forks?", client.received_prompt.user)
        self.assertIn("Move 2: Fork missed", client.received_prompt.user)
        self.assertIn("The candidate tactic was stronger", client.received_prompt.user)
        self.assertIn("Use only the supplied structured evidence.", client.received_prompt.system)

    def test_evidence_passthrough_reaches_prompt_builder_output(self) -> None:
        candidate = CandidateMove(
            move_uci="g5f7",
            move_san="Nf7+",
            start_fen=chess.STARTING_FEN,
            side=chess.WHITE,
        )
        event = make_verified_event(
            "fork_missed",
            evidence={
                "forking_piece_square": "f7",
                "target_squares": ("e5", "h8"),
                "target_pieces": ("k", "r"),
                "forking_move_san": "Nf7+",
            },
            candidate_move=candidate,
        )
        mate_event = make_verified_event(
            "fork_allowed",
            move_uci="b1c3",
            move_san="Nc3",
            event_score_kind="mate",
            impact_magnitude=None,
            impact_rank=9_999_998,
            candidate_score_after=EngineScore(mate=-2),
        )
        strength = make_pattern("fork_created", frequency=1, severity=200.0)
        execution_strength = make_pattern(
            "knight_outpost_created",
            frequency=3,
            severity=3.0,
        )
        weakness = make_pattern("fork_missed", supporting_events=(event,))
        profile = WeaknessProfile(
            strengths=(strength,),
            execution_strengths=(execution_strength,),
            weaknesses=(weakness,),
            recurring_themes=(weakness,),
        )
        client = RecordingLLMClient()

        LLMChatCoach(client=client).respond(
            "What should I study?",
            verified_events=(event, mate_event),
            patterns=(weakness,),
            weakness_profile=profile,
        )

        assert client.received_prompt is not None
        user_prompt = client.received_prompt.user
        self.assertIn("Execution strengths: Knight Outpost Created", user_prompt)
        self.assertIn("Fork Missed (fork_missed): frequency=2", user_prompt)
        self.assertIn("Candidate move: Nf7+ (g5f7), side=white", user_prompt)
        self.assertIn("Mate-aware rank impact: 9999998", user_prompt)
        self.assertNotIn("Mate-aware rank impact: 9999998 centipawns", user_prompt)

    def test_injected_prompt_builder_is_used(self) -> None:
        client = RecordingLLMClient()
        builder = RecordingPromptBuilder()
        moment = make_moment(make_verified_event())

        response = LLMChatCoach(client=client, prompt_builder=builder).respond(
            "Question?",
            coaching_moments=(moment,),
        )

        self.assertEqual(response, "grounded response")
        self.assertEqual(len(builder.calls), 1)
        self.assertEqual(builder.calls[0]["question"], "Question?")
        self.assertEqual(builder.calls[0]["coaching_moments"], (moment,))
        assert client.received_prompt is not None
        self.assertEqual(client.received_prompt.system, "custom system")
        self.assertEqual(client.received_prompt.user, "custom user")

    def test_invalid_client_and_prompt_builder_raise_type_error(self) -> None:
        with self.assertRaises(TypeError):
            LLMChatCoach(client=object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            LLMChatCoach(
                client=RecordingLLMClient(),
                prompt_builder=object(),  # type: ignore[arg-type]
            )

    def test_invalid_evidence_type_raises_through_prompt_builder(self) -> None:
        with self.assertRaises(TypeError):
            LLMChatCoach(client=RecordingLLMClient()).respond(
                "Question",
                verified_events=("1. e4 e5",),  # type: ignore[arg-type]
            )

    def test_client_exception_propagates(self) -> None:
        with self.assertRaises(RuntimeError):
            LLMChatCoach(client=FailingLLMClient()).respond("Question")

    def test_empty_evidence_still_calls_client_with_grounded_prompt(self) -> None:
        client = RecordingLLMClient()

        response = LLMChatCoach(client=client).respond("Can you help?")

        self.assertEqual(response, "grounded response")
        assert client.received_prompt is not None
        self.assertIn("No structured evidence supplied.", client.received_prompt.user)

    def test_llm_chat_coach_is_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(coaching.LLMChatCoach, LLMChatCoach)

    def test_source_has_no_provider_engine_or_chess_analysis_dependencies(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "llm_chat_coach.py"
        ).read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("stockfish", lower_source)
        self.assertNotIn("ai_chess_coach.engine", lower_source)
        self.assertNotIn("ai_chess_coach.detectors", lower_source)
        self.assertNotIn("featurestore", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("chess.board", lower_source)
        self.assertNotIn("board.attackers", source)
        self.assertNotIn("Board.attackers", source)
        self.assertNotIn("openai", lower_source)
        self.assertNotIn("anthropic", lower_source)
        self.assertNotIn("gemini", lower_source)
        self.assertNotIn("requests", lower_source)
        self.assertNotIn("httpx", lower_source)
        self.assertNotIn("socket", lower_source)
