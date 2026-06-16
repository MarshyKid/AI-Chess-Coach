from pathlib import Path
import unittest

import chess

from ai_chess_coach.models import (
    DetectedEvent,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
)
from ai_chess_coach.relevance import CoachingRelevancePolicy


def make_verified_event(
    event_type: str,
    *,
    event_impact_for_side: int | None,
    impact_magnitude: int | None,
    eval_delta_for_event_side: int | None = None,
    event_score_kind: str = "centipawn",
    event_impact_rank_for_side: int | None = None,
    impact_rank: int | None = None,
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
            eval_delta_for_event_side=eval_delta_for_event_side,
            impact_magnitude=impact_magnitude,
            event_impact_for_side=event_impact_for_side,
            event_score_kind=event_score_kind,  # type: ignore[arg-type]
            event_impact_rank_for_side=event_impact_rank_for_side,
            impact_rank=impact_rank,
        ),
    )


class CoachingRelevancePolicyTest(unittest.TestCase):
    def test_positive_event_is_relevant_only_when_it_helped_event_side(self) -> None:
        policy = CoachingRelevancePolicy()

        self.assertTrue(
            policy.is_relevant(
                make_verified_event(
                    "fork_created",
                    event_impact_for_side=100,
                    impact_magnitude=100,
                )
            )
        )
        self.assertFalse(
            policy.is_relevant(
                make_verified_event(
                    "fork_created",
                    event_impact_for_side=-100,
                    impact_magnitude=100,
                )
            )
        )

    def test_negative_event_is_relevant_only_when_it_hurt_event_side(self) -> None:
        policy = CoachingRelevancePolicy()

        self.assertTrue(
            policy.is_relevant(
                make_verified_event(
                    "fork_missed",
                    event_impact_for_side=-100,
                    impact_magnitude=100,
                )
            )
        )
        self.assertFalse(
            policy.is_relevant(
                make_verified_event(
                    "fork_missed",
                    event_impact_for_side=100,
                    impact_magnitude=100,
                )
            )
        )

    def test_neutral_unknown_missing_and_low_impact_events_are_not_relevant(self) -> None:
        policy = CoachingRelevancePolicy()

        events = (
            make_verified_event(
                "unregistered_event",
                event_impact_for_side=-100,
                impact_magnitude=100,
            ),
            make_verified_event(
                "hanging_piece_created",
                event_impact_for_side=None,
                impact_magnitude=100,
            ),
            make_verified_event(
                "hanging_piece_created",
                event_impact_for_side=-100,
                impact_magnitude=None,
            ),
            make_verified_event(
                "hanging_piece_created",
                event_impact_for_side=-79,
                impact_magnitude=79,
            ),
        )

        self.assertEqual(tuple(policy.is_relevant(event) for event in events), (False,) * 4)

    def test_threshold_is_configurable(self) -> None:
        event = make_verified_event(
            "hanging_piece_created",
            event_impact_for_side=-100,
            impact_magnitude=100,
        )

        self.assertTrue(CoachingRelevancePolicy(min_impact_centipawns=100).is_relevant(event))
        self.assertFalse(CoachingRelevancePolicy(min_impact_centipawns=101).is_relevant(event))

    def test_mate_events_use_rank_impact_and_polarity(self) -> None:
        policy = CoachingRelevancePolicy(min_impact_centipawns=10_000_000)
        relevant_negative = make_verified_event(
            "fork_missed",
            event_impact_for_side=None,
            impact_magnitude=None,
            event_score_kind="mate",
            event_impact_rank_for_side=-9_999_998,
            impact_rank=9_999_998,
        )
        mismatched_positive = make_verified_event(
            "fork_missed",
            event_impact_for_side=None,
            impact_magnitude=None,
            event_score_kind="mate",
            event_impact_rank_for_side=9_999_998,
            impact_rank=9_999_998,
        )
        missing_rank = make_verified_event(
            "fork_missed",
            event_impact_for_side=None,
            impact_magnitude=None,
            event_score_kind="mate",
            event_impact_rank_for_side=-9_999_998,
            impact_rank=None,
        )

        self.assertTrue(policy.is_relevant(relevant_negative))
        self.assertFalse(policy.is_relevant(mismatched_positive))
        self.assertFalse(policy.is_relevant(missing_rank))

    def test_negative_threshold_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            CoachingRelevancePolicy(min_impact_centipawns=-1)

    def test_non_verified_event_raises_type_error(self) -> None:
        with self.assertRaises(TypeError):
            CoachingRelevancePolicy().is_relevant("1. e4 e5")  # type: ignore[arg-type]

    def test_policy_is_exported_from_relevance_package(self) -> None:
        import ai_chess_coach.relevance as relevance

        self.assertIs(relevance.CoachingRelevancePolicy, CoachingRelevancePolicy)

    def test_policy_respects_architecture_boundaries(self) -> None:
        source = Path(
            "src/ai_chess_coach/relevance/coaching_relevance_policy.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("featurestore", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
