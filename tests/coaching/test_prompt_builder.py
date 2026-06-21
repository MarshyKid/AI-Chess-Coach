from inspect import signature
from pathlib import Path
import unittest

import chess

from ai_chess_coach.coaching import PromptBuilder
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


def make_verified_event(
    event_type: str = "hanging_piece_created",
    *,
    move_uci: str = "e2e4",
    move_san: str = "e4",
    side: chess.Color = chess.WHITE,
    squares: tuple[chess.Square, ...] = (chess.E4,),
    evidence: dict[str, object] | None = None,
    impact_magnitude: int | None = 120,
    event_score_kind: str = "centipawn",
    impact_rank: int | None = None,
    candidate_move: CandidateMove | None = None,
    candidate_score_after: EngineScore | None = None,
) -> VerifiedEvent:
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=side,
            move=chess.Move.from_uci(move_uci),
            position=chess.Board(),
            squares=squares,
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
            impact_rank=impact_rank,
            event_impact_rank_for_side=(
                impact_rank if impact_rank is not None else None
            ),
        ),
    )


def make_pattern(
    pattern_type: str,
    *,
    frequency: int = 2,
    severity: float = 120.0,
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
        title="Move 2: Piece safety issue",
        explanation="This move left a piece undefended.",
        supporting_evidence=(event,),
        position_reference="after-fen",
        highlights=(chess.E4,),
    )


class PromptBuilderTest(unittest.TestCase):
    def test_build_returns_deterministic_prompt(self) -> None:
        event = make_verified_event()
        builder = PromptBuilder()

        first = builder.build("What should I study?", verified_events=(event,))
        second = builder.build("What should I study?", verified_events=(event,))

        self.assertEqual(first, second)

    def test_prompt_includes_grounding_instructions_and_question(self) -> None:
        prompt = PromptBuilder().build("How should I improve?")

        self.assertIn("Use only the supplied structured evidence.", prompt.system)
        self.assertIn("Do not calculate moves.", prompt.system)
        self.assertIn("Do not analyze FENs independently.", prompt.system)
        self.assertIn("Treat FENs and position references as identifiers only.", prompt.system)
        self.assertIn(
            "Do not infer material, threats, legal moves, board features, or tactics from a FEN.",
            prompt.system,
        )
        self.assertIn("Do not analyze raw PGNs.", prompt.system)
        self.assertIn(
            "If Coaching Moments or a Weakness Profile are supplied, do not say there is no evidence.",
            prompt.system,
        )
        self.assertIn(
            "Do not ask the user for more game context unless no structured evidence is supplied.",
            prompt.system,
        )
        self.assertIn(
            "Base the answer mainly on Coaching Moments and Weakness Profile when they are supplied.",
            prompt.system,
        )
        self.assertIn(
            "Do not mention empty optional retrieved sections as evidence absence.",
            prompt.system,
        )
        self.assertIn("## User Question\nHow should I improve?", prompt.user)

    def test_prompt_separates_question_from_evidence_sections(self) -> None:
        prompt = PromptBuilder().build("Question text")

        self.assertLess(
            prompt.user.index("## User Question"),
            prompt.user.index("## Evidence Status"),
        )
        self.assertLess(
            prompt.user.index("## Evidence Status"),
            prompt.user.index("## Coaching Moments"),
        )
        self.assertNotIn("## Weakness Profile", prompt.user)
        self.assertNotIn("## Retrieved Patterns", prompt.user)
        self.assertNotIn("## Retrieved Verified Events", prompt.user)

    def test_coaching_moments_appear_first_and_use_detail_formatter(self) -> None:
        event = make_verified_event(
            evidence={
                "piece_square": "d4",
                "piece": "B",
                "piece_color": "white",
                "attackers": ("f6",),
                "defenders": (),
            },
        )
        moment = make_moment(event)
        pattern = make_pattern("hanging_piece_created", supporting_events=(event,))

        prompt = PromptBuilder().build(
            "What happened?",
            coaching_moments=(moment,),
            patterns=(pattern,),
        )

        self.assertLess(
            prompt.user.index("Move 2: Piece safety issue"),
            prompt.user.index("## Retrieved Patterns"),
        )
        self.assertIn(
            "Structured evidence is supplied. Base your answer on the supplied "
            "Coaching Moments and Weakness Profile.",
            prompt.user,
        )
        self.assertIn("Explanation: This move left a piece undefended.", prompt.user)
        self.assertIn(
            "Position reference only, do not analyze as FEN: after-fen",
            prompt.user,
        )
        self.assertIn("Highlights: e4", prompt.user)
        self.assertIn(
            "hanging_piece_created: white bishop on d4 became hanging; "
            "attackers: f6; defenders: none",
            prompt.user,
        )

    def test_weakness_profile_includes_execution_strengths(self) -> None:
        strength = make_pattern("fork_created", frequency=1, severity=200.0)
        execution_strength = make_pattern(
            "knight_outpost_created",
            frequency=3,
            severity=3.0,
        )
        weakness = make_pattern("fork_missed", frequency=2, severity=150.0)
        theme = make_pattern("hanging_piece_lost", frequency=4, severity=100.0)
        profile = WeaknessProfile(
            strengths=(strength,),
            execution_strengths=(execution_strength,),
            weaknesses=(weakness,),
            recurring_themes=(theme,),
        )

        prompt = PromptBuilder().build("Profile?", weakness_profile=profile)

        self.assertIn("High-impact strengths: Fork Created", prompt.user)
        self.assertIn("Execution strengths: Knight Outpost Created", prompt.user)
        self.assertIn("Weaknesses: Fork Missed", prompt.user)
        self.assertIn("Recurring themes: Hanging Piece Lost", prompt.user)

    def test_patterns_include_frequency_severity_and_supporting_event_count(self) -> None:
        event = make_verified_event()
        pattern = make_pattern(
            "hanging_piece_created",
            frequency=5,
            severity=175.5,
            supporting_events=(event,),
        )

        prompt = PromptBuilder().build("Patterns?", patterns=(pattern,))

        self.assertIn(
            "Hanging Piece Created (hanging_piece_created): "
            "frequency=5, severity=175.5, supporting_events=1",
            prompt.user,
        )

    def test_verified_event_includes_fields_and_candidate_move_details(self) -> None:
        candidate = CandidateMove(
            move_uci="g5f7",
            move_san="Nf7+",
            start_fen=chess.STARTING_FEN,
            side=chess.WHITE,
        )
        event = make_verified_event(
            "fork_missed",
            move_uci="a2a3",
            move_san="a3",
            squares=(chess.F7,),
            evidence={
                "forking_piece_square": "f7",
                "target_squares": ("e5", "h8"),
                "target_pieces": ("k", "r"),
                "forking_move_san": "Nf7+",
            },
            impact_magnitude=240,
            candidate_move=candidate,
        )

        prompt = PromptBuilder().build("Any tactics?", verified_events=(event,))

        self.assertIn("Fork Missed (fork_missed)", prompt.user)
        self.assertIn("Side: white", prompt.user)
        self.assertIn("Ply: 3", prompt.user)
        self.assertIn("Move: a3 (a2a3)", prompt.user)
        self.assertIn("Squares: f7", prompt.user)
        self.assertIn("Score kind: centipawn", prompt.user)
        self.assertIn("Centipawn impact: 240 centipawns", prompt.user)
        self.assertIn("Candidate move: Nf7+ (g5f7), side=white", prompt.user)
        self.assertIn(
            "fork_missed: candidate Nf7+ from f7 attacked king on e5 and rook on h8",
            prompt.user,
        )

    def test_mate_rank_is_not_described_as_centipawns(self) -> None:
        event = make_verified_event(
            "fork_allowed",
            event_score_kind="mate",
            impact_magnitude=None,
            impact_rank=9_999_998,
            candidate_score_after=EngineScore(mate=-2),
        )

        prompt = PromptBuilder().build("Mate issue?", verified_events=(event,))

        self.assertIn("Score kind: mate", prompt.user)
        self.assertIn("Mate-aware rank impact: 9999998", prompt.user)
        self.assertNotIn("Mate-aware rank impact: 9999998 centipawns", prompt.user)

    def test_empty_evidence_is_handled_safely(self) -> None:
        prompt = PromptBuilder().build("What can you tell me?")

        self.assertIn("## Coaching Moments\nNone supplied.", prompt.user)
        self.assertNotIn("## Weakness Profile", prompt.user)
        self.assertNotIn("## Retrieved Patterns", prompt.user)
        self.assertNotIn("## Retrieved Verified Events", prompt.user)
        self.assertIn(
            "## Evidence Status\nNo structured evidence supplied. Say what evidence is missing.",
            prompt.user,
        )

    def test_invalid_input_types_raise_type_error(self) -> None:
        builder = PromptBuilder()
        event = make_verified_event()

        with self.assertRaises(TypeError):
            builder.build(123)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", coaching_moments=("1. e4 e5",))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", coaching_moments=object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", verified_events=(event.event,))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", verified_events=object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", patterns=(event,))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", patterns=object())  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            builder.build("Question", weakness_profile=object())  # type: ignore[arg-type]

    def test_raw_pgn_protection_is_structural_but_question_notation_is_allowed(self) -> None:
        prompt = PromptBuilder().build("After 1. e4 e5 2. Nf3, what should I review?")

        self.assertIn("After 1. e4 e5 2. Nf3, what should I review?", prompt.user)

        with self.assertRaises(TypeError):
            PromptBuilder().build("Question", verified_events=("1. e4 e5",))  # type: ignore[arg-type]

    def test_signature_exposes_no_raw_pgn_input_path(self) -> None:
        parameters = set(signature(PromptBuilder.build).parameters)

        self.assertNotIn("pgn_text", parameters)
        self.assertNotIn("raw_pgn", parameters)

    def test_prompt_builder_is_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(coaching.PromptBuilder, PromptBuilder)

    def test_source_has_no_provider_engine_or_chess_analysis_dependencies(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "prompt_builder.py"
        ).read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("stockfish", lower_source)
        self.assertNotIn("ai_chess_coach.engine", lower_source)
        self.assertNotIn("ai_chess_coach.detectors", lower_source)
        self.assertNotIn("featurestore", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("board.attackers", source)
        self.assertNotIn("Board.attackers", source)
        self.assertNotIn("openai", lower_source)
        self.assertNotIn("anthropic", lower_source)
        self.assertNotIn("gemini", lower_source)
        self.assertNotIn("requests", lower_source)
        self.assertNotIn("httpx", lower_source)
        self.assertNotIn("socket", lower_source)
