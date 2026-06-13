from pathlib import Path
import unittest

from ai_chess_coach.coaching import ChatCoach
from ai_chess_coach.models import CoachingMoment


def make_moment(
    title: str,
    explanation: str = "This is grounded in supplied coaching evidence.",
    *,
    position_reference: str | None = None,
) -> CoachingMoment:
    return CoachingMoment(
        title=title,
        explanation=explanation,
        supporting_evidence=(),
        position_reference=position_reference,
        highlights=(),
    )


class ChatCoachTest(unittest.TestCase):
    def test_respond_returns_string(self) -> None:
        response = ChatCoach().respond(
            "What should I review?",
            (make_moment("Review Loose Pieces"),),
        )

        self.assertIsInstance(response, str)

    def test_response_includes_selected_moment_title_and_explanation(self) -> None:
        moment = make_moment(
            "Review Loose Pieces",
            "Your loose pieces repeatedly became tactical targets.",
        )

        response = ChatCoach().respond("What should I review?", (moment,))

        self.assertIn("Review Loose Pieces", response)
        self.assertIn("Your loose pieces repeatedly became tactical targets.", response)

    def test_response_includes_position_reference_when_available(self) -> None:
        moment = make_moment(
            "Review Loose Pieces",
            position_reference="8/8/8/8/8/8/8/8 w - - 0 1",
        )

        response = ChatCoach().respond("loose pieces", (moment,))

        self.assertIn("Position: 8/8/8/8/8/8/8/8 w - - 0 1", response)

    def test_response_omits_position_line_when_position_reference_unavailable(self) -> None:
        moment = make_moment("Review Loose Pieces", position_reference=None)

        response = ChatCoach().respond("loose pieces", (moment,))

        self.assertNotIn("Position:", response)

    def test_empty_moments_returns_clear_no_evidence_message(self) -> None:
        response = ChatCoach().respond("What should I study?", ())

        self.assertEqual(response, "No coaching evidence is available yet.")

    def test_matching_title_words_select_matching_moment(self) -> None:
        first = make_moment("Review Loose Pieces", "First explanation.")
        second = make_moment("Practice Fork Awareness", "Second explanation.")

        response = ChatCoach().respond("How do I improve forks?", (first, second))

        self.assertIn("Practice Fork Awareness", response)
        self.assertIn("Second explanation.", response)

    def test_no_title_match_falls_back_to_first_moment(self) -> None:
        first = make_moment("Review Loose Pieces", "First explanation.")
        second = make_moment("Practice Fork Awareness", "Second explanation.")

        response = ChatCoach().respond("How should I train endgames?", (first, second))

        self.assertIn("Review Loose Pieces", response)
        self.assertIn("First explanation.", response)

    def test_raw_pgn_strings_and_unsupported_objects_raise_type_error(self) -> None:
        coach = ChatCoach()

        with self.assertRaises(TypeError):
            coach.respond("What happened?", ("1. e4 e5",))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            coach.respond("What happened?", (object(),))  # type: ignore[arg-type]

    def test_source_does_not_import_engine_llms_pgn_or_direct_chess_analysis(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "chat_coach.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("chess.pgn", source)
        self.assertNotIn("legal_moves", source)
        self.assertNotIn("attackers", source)

    def test_chat_coach_is_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(coaching.ChatCoach, ChatCoach)
