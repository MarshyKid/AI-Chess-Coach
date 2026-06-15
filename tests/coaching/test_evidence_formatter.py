from pathlib import Path
import unittest

import chess

from ai_chess_coach.coaching import (
    format_coaching_moment_details,
    format_supporting_event_detail,
)
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    EngineAssessment,
    EventMetadata,
    VerifiedEvent,
    WeaknessProfile,
)


def make_verified_event(
    event_type: str,
    *,
    evidence: dict[str, object] | None = None,
    move_san: str = "e4",
    impact_magnitude: int | None = 120,
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
                after_fen="after-fen",
                move_uci=move.uci(),
                move_san=move_san,
                ply=1,
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
            eval_delta_for_event_side=impact_magnitude,
            impact_magnitude=impact_magnitude,
        ),
    )


class EvidenceFormatterTest(unittest.TestCase):
    def test_formats_hanging_piece_created_detail(self) -> None:
        event = make_verified_event(
            "hanging_piece_created",
            evidence={
                "piece_square": "d4",
                "piece": "B",
                "piece_color": "white",
                "attackers": ("f6", "g7"),
                "defenders": (),
            },
        )

        detail = format_supporting_event_detail(event)

        self.assertEqual(
            detail,
            "hanging_piece_created: white bishop on d4 became hanging; "
            "attackers: f6, g7; defenders: none",
        )

    def test_formats_hanging_piece_lost_detail(self) -> None:
        event = make_verified_event(
            "hanging_piece_lost",
            evidence={
                "piece_square": "d4",
                "piece": "n",
                "piece_color": "black",
                "attackers": ("d1",),
                "defenders": (),
                "captured_square": "d4",
                "captured_piece": "n",
            },
        )

        detail = format_supporting_event_detail(event)

        self.assertEqual(
            detail,
            "hanging_piece_lost: black knight on d4 was captured while hanging; "
            "captured knight on d4; attackers: d1; defenders: none",
        )

    def test_formats_fork_missed_detail_with_target_pieces(self) -> None:
        event = make_verified_event(
            "fork_missed",
            evidence={
                "forking_piece_square": "f7",
                "forking_piece": "N",
                "forking_piece_color": "white",
                "target_squares": ("e5", "h8"),
                "target_pieces": ("k", "r"),
                "forking_move_uci": "g5f7",
                "forking_move_san": "Nf7+",
            },
        )

        detail = format_supporting_event_detail(event)

        self.assertEqual(
            detail,
            "fork_missed: candidate Nf7+ from f7 attacked king on e5 and rook on h8",
        )

    def test_formats_fork_allowed_detail_without_target_pieces(self) -> None:
        event = make_verified_event(
            "fork_allowed",
            evidence={
                "forking_piece_square": "f6",
                "target_squares": ("e8", "g8"),
                "forking_move_uci": "h7f6",
            },
        )

        detail = format_supporting_event_detail(event)

        self.assertEqual(
            detail,
            "fork_allowed: candidate h7f6 from f6 attacked targets on e8 and g8",
        )

    def test_formats_knight_outpost_missed_detail(self) -> None:
        event = make_verified_event(
            "knight_outpost_missed",
            evidence={
                "knight_square": "d5",
                "knight_color": "white",
                "defending_pawn_squares": ("c4", "e4"),
                "enemy_pawn_attack_squares": (),
                "outpost_move_uci": "f4d5",
                "outpost_move_san": "Nd5",
            },
        )

        detail = format_supporting_event_detail(event)

        self.assertEqual(
            detail,
            "knight_outpost_missed: candidate Nd5 created an outpost on d5; "
            "defended by pawns: c4, e4; enemy pawn attacks: none",
        )

    def test_formats_unknown_event_type_with_safe_fallback(self) -> None:
        event = make_verified_event(
            "new_event_type",
            move_san="Nf3",
            impact_magnitude=95,
        )

        detail = format_supporting_event_detail(event)

        self.assertEqual(
            detail,
            "New Event Type: selected event on move Nf3 with impact 95 centipawns",
        )

    def test_format_coaching_moment_details_returns_one_line_per_verified_event(
        self,
    ) -> None:
        first = make_verified_event(
            "hanging_piece_created",
            evidence={
                "piece_square": "d4",
                "piece": "B",
                "piece_color": "white",
            },
        )
        second = make_verified_event(
            "fork_missed",
            evidence={
                "forking_piece_square": "f7",
                "target_squares": ("e5", "h8"),
                "forking_move_san": "Nf7+",
            },
        )
        moment = CoachingMoment(
            title="Grouped",
            explanation="Summary",
            supporting_evidence=(first, second),
            position_reference=None,
            highlights=(),
        )

        details = format_coaching_moment_details(moment)

        self.assertEqual(len(details), 2)
        self.assertTrue(details[0].startswith("hanging_piece_created:"))
        self.assertTrue(details[1].startswith("fork_missed:"))

    def test_format_coaching_moment_details_skips_non_verified_evidence(self) -> None:
        event = make_verified_event("new_event_type")
        profile = WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=())
        moment = CoachingMoment(
            title="Mixed evidence",
            explanation="Summary",
            supporting_evidence=(event, profile),
            position_reference=None,
            highlights=(),
        )

        details = format_coaching_moment_details(moment)

        self.assertEqual(len(details), 1)
        self.assertTrue(details[0].startswith("New Event Type:"))

    def test_formatter_is_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(
            coaching.format_supporting_event_detail,
            format_supporting_event_detail,
        )
        self.assertIs(
            coaching.format_coaching_moment_details,
            format_coaching_moment_details,
        )

    def test_formatter_respects_architecture_boundaries(self) -> None:
        source = Path(
            "src/ai_chess_coach/coaching/evidence_formatter.py"
        ).read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("stockfish", lower_source)
        self.assertNotIn("ai_chess_coach.engine", lower_source)
        self.assertNotIn("openai", lower_source)
        self.assertNotIn("llm", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("attackers", lower_source)
        self.assertNotIn("FeatureStore", source)
