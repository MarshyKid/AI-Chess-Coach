from pathlib import Path
import unittest

import chess

from ai_chess_coach.coaching import CoachingMomentSelector
from ai_chess_coach.coaching.coaching_moment_selector import VerifiedEventGroup
from ai_chess_coach.models import (
    DetectedEvent,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
)


def make_verified_event(
    event_type: str,
    *,
    side: chess.Color = chess.WHITE,
    ply: int = 1,
    move_uci: str = "e2e4",
    squares: tuple[chess.Square, ...] = (chess.E4,),
    eval_delta_for_event_side: int | None = -100,
    event_impact_for_side: int | None = None,
    impact_magnitude: int | None = 100,
) -> VerifiedEvent:
    computed_event_impact_for_side = (
        event_impact_for_side
        if event_impact_for_side is not None
        else eval_delta_for_event_side
    )
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
                move_san=move_uci,
                ply=ply,
            ),
            evidence={},
            severity=1.0,
        ),
        engine_assessment=EngineAssessment(
            eval_before=0,
            eval_after=eval_delta_for_event_side,
            eval_delta=eval_delta_for_event_side,
            best_move=None,
            principal_variation=(),
            depth=10,
            eval_delta_for_event_side=eval_delta_for_event_side,
            impact_magnitude=impact_magnitude,
            event_impact_for_side=computed_event_impact_for_side,
        ),
    )


class CoachingMomentSelectorTest(unittest.TestCase):
    def test_low_impact_events_are_filtered_out(self) -> None:
        event = make_verified_event("hanging_piece_created", impact_magnitude=79)

        groups = CoachingMomentSelector().select((event,))

        self.assertEqual(groups, ())

    def test_positive_events_are_kept_only_when_they_help_event_side(self) -> None:
        kept = make_verified_event(
            "fork_created",
            eval_delta_for_event_side=100,
            impact_magnitude=100,
        )
        filtered = make_verified_event(
            "fork_created",
            eval_delta_for_event_side=-100,
            impact_magnitude=100,
            move_uci="g1f3",
        )

        groups = CoachingMomentSelector().select((kept, filtered))

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].events, (kept,))

    def test_selector_uses_event_impact_for_polarity_not_actual_move_delta(
        self,
    ) -> None:
        event = make_verified_event(
            "fork_missed",
            eval_delta_for_event_side=-500,
            event_impact_for_side=100,
            impact_magnitude=100,
        )

        groups = CoachingMomentSelector().select((event,))

        self.assertEqual(groups, ())

    def test_negative_events_are_kept_only_when_they_hurt_event_side(self) -> None:
        kept = make_verified_event(
            "fork_missed",
            eval_delta_for_event_side=-100,
            impact_magnitude=100,
        )
        filtered = make_verified_event(
            "fork_missed",
            eval_delta_for_event_side=100,
            impact_magnitude=100,
            move_uci="g1f3",
        )

        groups = CoachingMomentSelector().select((kept, filtered))

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].events, (kept,))

    def test_neutral_unknown_and_missing_impact_events_are_not_promoted(self) -> None:
        neutral = make_verified_event(
            "unregistered_event",
            eval_delta_for_event_side=-100,
            impact_magnitude=100,
        )
        missing_impact = make_verified_event(
            "hanging_piece_created",
            eval_delta_for_event_side=-100,
            impact_magnitude=None,
            move_uci="g1f3",
        )

        groups = CoachingMomentSelector().select((neutral, missing_impact))

        self.assertEqual(groups, ())

    def test_same_ply_side_category_and_polarity_events_are_not_grouped(self) -> None:
        first = make_verified_event(
            "fork_missed",
            ply=7,
            move_uci="g1f3",
            squares=(chess.F3,),
        )
        second = make_verified_event(
            "fork_allowed",
            ply=7,
            move_uci="b1c3",
            squares=(chess.C3,),
        )

        groups = CoachingMomentSelector().select((first, second))

        self.assertEqual(len(groups), 2)
        self.assertTrue(all(isinstance(group, VerifiedEventGroup) for group in groups))
        self.assertEqual(tuple(group.events for group in groups), ((second,), (first,)))
        self.assertTrue(all(len(group.events) == 1 for group in groups))
        self.assertTrue(all(group.category == "tactics" for group in groups))
        self.assertTrue(all(group.polarity == "negative" for group in groups))

    def test_different_side_or_polarity_events_are_not_grouped(self) -> None:
        white_negative = make_verified_event("fork_missed", side=chess.WHITE)
        black_negative = make_verified_event("fork_missed", side=chess.BLACK)
        white_positive = make_verified_event(
            "fork_created",
            side=chess.WHITE,
            eval_delta_for_event_side=100,
            impact_magnitude=100,
        )

        groups = CoachingMomentSelector().select(
            (white_negative, black_negative, white_positive)
        )

        self.assertEqual(len(groups), 3)
        self.assertTrue(all(len(group.events) == 1 for group in groups))

    def test_groups_are_ranked_by_impact_and_limited(self) -> None:
        events = tuple(
            make_verified_event(
                "hanging_piece_created",
                ply=ply,
                move_uci=f"a{ply}a{ply + 1}",
                eval_delta_for_event_side=-impact,
                impact_magnitude=impact,
            )
            for ply, impact in enumerate((100, 300, 200, 500, 400, 600), start=1)
        )

        groups = CoachingMomentSelector().select(events)

        self.assertEqual(len(groups), 5)
        self.assertEqual(
            tuple(group.impact_magnitude for group in groups),
            (600, 500, 400, 300, 200),
        )
        self.assertTrue(all(len(group.events) == 1 for group in groups))

    def test_tie_breaking_uses_stable_event_fields(self) -> None:
        later_move = make_verified_event(
            "fork_missed",
            ply=2,
            move_uci="g1f3",
            squares=(chess.F3,),
        )
        earlier_move = make_verified_event(
            "fork_allowed",
            ply=1,
            move_uci="b1c3",
            squares=(chess.C3,),
        )

        groups = CoachingMomentSelector().select((later_move, earlier_move))

        self.assertEqual(tuple(group.events[0] for group in groups), (earlier_move, later_move))

    def test_invalid_items_raise_type_error(self) -> None:
        with self.assertRaises(TypeError):
            CoachingMomentSelector().select(("1. e4 e5",))  # type: ignore[arg-type]

    def test_selector_is_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(coaching.CoachingMomentSelector, CoachingMomentSelector)

    def test_selector_respects_architecture_boundaries(self) -> None:
        source = Path(
            "src/ai_chess_coach/coaching/coaching_moment_selector.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)
        self.assertNotIn("featurestore", source)
