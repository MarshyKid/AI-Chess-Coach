from pathlib import Path
import unittest

import chess

from ai_chess_coach.coaching import LLMPrompt, PromptBuilder
from ai_chess_coach.coaching.prompt_builder import NO_EVIDENCE_MESSAGE
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
    WeaknessProfile,
)


def make_verified_event(
    event_type: str = "hanging_piece_created",
    *,
    evidence: dict[str, object] | None = None,
    move_san: str = "e4",
    move_uci: str = "e2e4",
    ply: int = 1,
    side: chess.Color = chess.WHITE,
    impact_magnitude: int | None = 120,
    event_score_kind: str = "centipawn",
    impact_rank: int | None = None,
    candidate_move_uci: str | None = None,
) -> VerifiedEvent:
    move = chess.Move.from_uci(move_uci)
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=side,
            move=move,
            position=chess.Board(),
            squares=(chess.E4,),
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen="after-fen",
                move_uci=move_uci,
                move_san=move_san,
                ply=ply,
            ),
            evidence=evidence or {},
            severity=1.0,
        ),
        engine_assessment=EngineAssessment(
            eval_before=0,
            eval_after=impact_magnitude,
            eval_delta=impact_magnitude,
            best_move=None,
            principal_variation=(),
            depth=10,
            impact_magnitude=impact_magnitude,
            candidate_move_uci=candidate_move_uci,
            event_score_kind=event_score_kind,  # type: ignore[arg-type]
            impact_rank=impact_rank,
        ),
    )


def make_pattern(
    pattern_type: str = "hanging_piece_weakness",
    *,
    frequency: int = 3,
    severity: float = 0.75,
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pattern_type,
        frequency=frequency,
        severity=severity,
        supporting_events=(make_verified_event(),),
    )


def make_moment(
    title: str = "Move 1: Piece safety issue",
    *,
    explanation: str = "Your bishop was left hanging.",
    position_reference: str | None = "fen-reference",
) -> CoachingMoment:
    return CoachingMoment(
        title=title,
        explanation=explanation,
        supporting_evidence=(
            make_verified_event(
                "hanging_piece_created",
                evidence={
                    "piece_square": "d4",
                    "piece": "B",
                    "piece_color": "white",
                    "attackers": ("f6",),
                    "defenders": (),
                },
            ),
        ),
        position_reference=position_reference,
        highlights=(chess.D4,),
    )


class PromptBuilderTest(unittest.TestCase):
    def test_returns_llm_prompt_with_system_and_user(self) -> None:
        prompt = PromptBuilder().build("Why do I lose pieces?")

        self.assertIsInstance(prompt, LLMPrompt)
        self.assertTrue(prompt.system)
        self.assertIn("## PLAYER QUESTION", prompt.user)

    def test_system_section_contains_grounding_rules(self) -> None:
        system = PromptBuilder().build("question").system

        self.assertIn("Use only the evidence", system)
        self.assertIn("Do not calculate moves", system)
        self.assertIn("Do not analyze FEN", system)
        self.assertIn("raw PGN", system)
        self.assertIn("primary teaching points", system)

    def test_is_deterministic(self) -> None:
        builder = PromptBuilder()
        moment = make_moment()
        event = make_verified_event()
        profile = WeaknessProfile(
            strengths=(), weaknesses=(make_pattern(),), recurring_themes=()
        )

        first = builder.build(
            "why?",
            coaching_moments=(moment,),
            verified_events=(event,),
            patterns=(make_pattern(),),
            weakness_profile=profile,
        )
        second = builder.build(
            "why?",
            coaching_moments=(moment,),
            verified_events=(event,),
            patterns=(make_pattern(),),
            weakness_profile=profile,
        )

        self.assertEqual(first, second)

    def test_question_is_isolated_under_its_own_header(self) -> None:
        prompt = PromptBuilder().build("Why do I keep blundering bishops?")

        user = prompt.user
        self.assertIn("## PLAYER QUESTION\nWhy do I keep blundering bishops?", user)

    def test_coaching_moments_appear_before_other_evidence(self) -> None:
        prompt = PromptBuilder().build(
            "why?",
            coaching_moments=(make_moment(),),
            verified_events=(make_verified_event(),),
            patterns=(make_pattern(),),
            weakness_profile=WeaknessProfile(
                strengths=(), weaknesses=(make_pattern(),), recurring_themes=()
            ),
        )

        user = prompt.user
        self.assertLess(
            user.index("## SELECTED COACHING MOMENTS"),
            user.index("## WEAKNESS PROFILE"),
        )
        self.assertLess(
            user.index("## WEAKNESS PROFILE"),
            user.index("## RETRIEVED PATTERNS"),
        )
        self.assertLess(
            user.index("## RETRIEVED PATTERNS"),
            user.index("## SUPPORTING VERIFIED EVENTS"),
        )

    def test_coaching_moment_uses_existing_formatter_details(self) -> None:
        prompt = PromptBuilder().build("why?", coaching_moments=(make_moment(),))

        user = prompt.user
        self.assertIn("Move 1: Piece safety issue", user)
        self.assertIn("Your bishop was left hanging.", user)
        self.assertIn("Position reference: fen-reference", user)
        self.assertIn("Highlights: d4", user)
        self.assertIn("white bishop on d4 became hanging", user)

    def test_weakness_profile_includes_all_categories(self) -> None:
        profile = WeaknessProfile(
            strengths=(make_pattern("fork_strength"),),
            weaknesses=(make_pattern("hanging_piece_weakness"),),
            recurring_themes=(make_pattern("loose_piece_theme"),),
            execution_strengths=(make_pattern("knight_outpost_created"),),
        )

        user = PromptBuilder().build("why?", weakness_profile=profile).user

        self.assertIn("High-impact strengths: fork_strength", user)
        self.assertIn("Execution strengths: knight_outpost_created", user)
        self.assertIn("Weaknesses: hanging_piece_weakness", user)
        self.assertIn("Recurring themes: loose_piece_theme", user)

    def test_empty_profile_categories_render_none(self) -> None:
        profile = WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=())

        user = PromptBuilder().build("why?", weakness_profile=profile).user

        self.assertIn("High-impact strengths: none", user)
        self.assertIn("Execution strengths: none", user)

    def test_patterns_include_frequency_severity_and_event_count(self) -> None:
        pattern = make_pattern("fork_missed_pattern", frequency=4, severity=0.5)

        user = PromptBuilder().build("why?", patterns=(pattern,)).user

        self.assertIn(
            "fork_missed_pattern (frequency=4, severity=0.5, supporting_events=1)",
            user,
        )

    def test_verified_event_header_includes_core_fields(self) -> None:
        event = make_verified_event(
            "fork_missed",
            move_san="Nf7+",
            move_uci="g5f7",
            ply=15,
            side=chess.BLACK,
            candidate_move_uci="g5f7",
            evidence={
                "forking_move_san": "Nf7+",
                "forking_piece_square": "f7",
                "target_squares": ("e5", "h8"),
                "target_pieces": ("k", "r"),
            },
        )

        user = PromptBuilder().build("why?", verified_events=(event,)).user

        self.assertIn("fork_missed", user)
        self.assertIn("move Nf7+ (g5f7)", user)
        self.assertIn("ply 15", user)
        self.assertIn("side black", user)
        self.assertIn("candidate move g5f7", user)

    def test_centipawn_event_reports_centipawns_not_mate(self) -> None:
        event = make_verified_event(
            event_score_kind="centipawn", impact_magnitude=240
        )

        user = PromptBuilder().build("why?", verified_events=(event,)).user

        self.assertIn("impact 240 centipawns", user)
        self.assertNotIn("mate-aware rank", user)

    def test_mate_scored_event_never_reports_centipawns(self) -> None:
        event = make_verified_event(
            "fork_missed",
            event_score_kind="mate",
            impact_magnitude=None,
            impact_rank=3,
            evidence={
                "forking_move_san": "Nf7+",
                "forking_piece_square": "f7",
                "target_squares": ("e5", "h8"),
                "target_pieces": ("k", "r"),
            },
        )

        user = PromptBuilder().build("why?", verified_events=(event,)).user

        self.assertIn("mate-aware rank impact 3", user)
        self.assertNotIn("centipawns", user)

    def test_empty_evidence_is_handled_explicitly(self) -> None:
        user = PromptBuilder().build("Any advice?").user

        self.assertIn(NO_EVIDENCE_MESSAGE, user)
        self.assertNotIn("## SELECTED COACHING MOMENTS", user)

    def test_raw_pgn_tag_blob_is_rejected(self) -> None:
        pgn = (
            '[Event "Casual Game"]\n'
            '[Site "?"]\n'
            '[Result "1-0"]\n\n'
            "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n"
        )

        with self.assertRaisesRegex(ValueError, "raw PGN"):
            PromptBuilder().build(pgn)

    def test_long_move_number_blob_is_rejected(self) -> None:
        blob = " ".join(f"{n}. e4 e5" for n in range(1, 12))

        with self.assertRaises(ValueError):
            PromptBuilder().build(blob)

    def test_ordinary_question_with_notation_is_accepted(self) -> None:
        question = "Why was 1.e4 e5 2.Nf3 a weak setup for my pieces?"

        prompt = PromptBuilder().build(question)

        self.assertIn(question, prompt.user)

    def test_rejects_non_coaching_moment_inputs(self) -> None:
        with self.assertRaises(TypeError):
            PromptBuilder().build("why?", coaching_moments=(make_pattern(),))  # type: ignore[arg-type]


class PromptBuilderBoundaryTest(unittest.TestCase):
    def test_module_does_not_import_engine_or_provider_sdks(self) -> None:
        path = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "prompt_builder.py"
        )
        source = path.read_text(encoding="utf-8").lower()
        for forbidden in (
            "stockfish",
            "ai_chess_coach.engine",
            "ai_chess_coach.detectors",
            "featurestore",
            "legal_moves",
            "attackers",
            "anthropic",
            "openai",
            "gemini",
            "requests",
            "httpx",
        ):
            self.assertNotIn(forbidden, source, forbidden)


if __name__ == "__main__":
    unittest.main()
