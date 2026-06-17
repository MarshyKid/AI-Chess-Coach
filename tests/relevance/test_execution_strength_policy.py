from pathlib import Path
import unittest

import chess

from ai_chess_coach.models import (
    DetectedEvent,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
)
from ai_chess_coach.relevance import ExecutionStrengthPolicy


def make_verified_event(
    event_type: str,
    *,
    event_impact_for_side: int | None,
    event_score_kind: str = "centipawn",
    event_impact_rank_for_side: int | None = None,
) -> VerifiedEvent:
    move = chess.Move.from_uci("e2e4")
    return VerifiedEvent(
        event=DetectedEvent(
            event_type=event_type,
            side=chess.WHITE,
            move=move,
            position=chess.Board(),
            squares=(chess.E4,),
            metadata=EventMetadata(
                before_fen=chess.STARTING_FEN,
                after_fen=chess.Board().fen(),
                move_uci=move.uci(),
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
            event_impact_for_side=event_impact_for_side,
            event_score_kind=event_score_kind,  # type: ignore[arg-type]
            event_impact_rank_for_side=event_impact_rank_for_side,
        ),
    )


class ExecutionStrengthPolicyTest(unittest.TestCase):
    def test_accepts_low_impact_positive_execution_events(self) -> None:
        policy = ExecutionStrengthPolicy()

        self.assertTrue(
            policy.is_execution_strength(
                make_verified_event("fork_created", event_impact_for_side=1)
            )
        )
        self.assertTrue(
            policy.is_execution_strength(
                make_verified_event("knight_outpost_created", event_impact_for_side=1)
            )
        )

    def test_accepts_zero_impact_positive_execution_events(self) -> None:
        event = make_verified_event("fork_created", event_impact_for_side=0)

        self.assertTrue(ExecutionStrengthPolicy().is_execution_strength(event))

    def test_accepts_non_negative_mate_rank_execution_events(self) -> None:
        event = make_verified_event(
            "fork_created",
            event_impact_for_side=None,
            event_score_kind="mate",
            event_impact_rank_for_side=0,
        )

        self.assertTrue(ExecutionStrengthPolicy().is_execution_strength(event))

    def test_rejects_negative_neutral_unknown_and_non_execution_events(self) -> None:
        policy = ExecutionStrengthPolicy()
        events = (
            make_verified_event("fork_missed", event_impact_for_side=100),
            make_verified_event("time_pressure_pattern", event_impact_for_side=100),
            make_verified_event("hanging_piece_created", event_impact_for_side=100),
        )

        self.assertEqual(
            tuple(policy.is_execution_strength(event) for event in events),
            (False, False, False),
        )

    def test_rejects_contradicted_execution_events(self) -> None:
        policy = ExecutionStrengthPolicy()
        centipawn_event = make_verified_event(
            "fork_created",
            event_impact_for_side=-1,
        )
        mate_event = make_verified_event(
            "knight_outpost_created",
            event_impact_for_side=None,
            event_score_kind="mate",
            event_impact_rank_for_side=-1,
        )

        self.assertFalse(policy.is_execution_strength(centipawn_event))
        self.assertFalse(policy.is_execution_strength(mate_event))

    def test_rejects_unavailable_or_missing_impact(self) -> None:
        policy = ExecutionStrengthPolicy()
        unavailable = make_verified_event(
            "fork_created",
            event_impact_for_side=None,
            event_score_kind="unavailable",
        )
        missing_centipawn = make_verified_event(
            "fork_created",
            event_impact_for_side=None,
        )
        missing_mate = make_verified_event(
            "fork_created",
            event_impact_for_side=None,
            event_score_kind="mate",
            event_impact_rank_for_side=None,
        )

        self.assertFalse(policy.is_execution_strength(unavailable))
        self.assertFalse(policy.is_execution_strength(missing_centipawn))
        self.assertFalse(policy.is_execution_strength(missing_mate))

    def test_non_verified_event_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            ExecutionStrengthPolicy().is_execution_strength("1. e4 e5")  # type: ignore[arg-type]

    def test_policy_is_exported_from_relevance_package(self) -> None:
        import ai_chess_coach.relevance as relevance

        self.assertIs(relevance.ExecutionStrengthPolicy, ExecutionStrengthPolicy)

    def test_policy_respects_architecture_boundaries(self) -> None:
        source = Path(
            "src/ai_chess_coach/relevance/execution_strength_policy.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("featurestore", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
