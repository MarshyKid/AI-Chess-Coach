import inspect
import unittest
from dataclasses import fields
from unittest.mock import Mock, patch

import chess

import ai_chess_coach.detectors.knight_outpost_detector as knight_outpost_detector
from ai_chess_coach.detectors import BaseDetector, KnightOutpostDetector
from ai_chess_coach.models import CandidateMove, DetectedEvent, MoveTransition


def make_transition(fen: str, uci: str) -> MoveTransition:
    before = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    if move not in before.legal_moves:
        raise ValueError(f"{uci} is not legal in {fen}")

    san = before.san(move)
    after = before.copy(stack=False)
    after.push(move)

    return MoveTransition(
        ply=1,
        san=san,
        move=move,
        before_position=before.copy(stack=False),
        after_position=after.copy(stack=False),
    )


def assert_event_metadata(
    test_case: unittest.TestCase,
    event: DetectedEvent,
    transition: MoveTransition,
) -> None:
    test_case.assertEqual(event.metadata.before_fen, transition.before_position.fen())
    test_case.assertEqual(event.metadata.after_fen, transition.after_position.fen())
    test_case.assertEqual(event.metadata.move_uci, transition.move.uci())
    test_case.assertEqual(event.metadata.move_san, transition.san)
    test_case.assertEqual(event.metadata.ply, transition.ply)


def events_of_type(events: list[DetectedEvent], event_type: str) -> list[DetectedEvent]:
    return [event for event in events if event.event_type == event_type]


class KnightOutpostDetectorTest(unittest.TestCase):
    def test_detector_inherits_base_detector(self) -> None:
        self.assertIsInstance(KnightOutpostDetector(), BaseDetector)

    def test_no_events_when_no_knight_outpost_exists(self) -> None:
        transition = make_transition(chess.STARTING_FEN, "e2e4")

        events = KnightOutpostDetector().detect(transition)

        self.assertEqual(events, [])

    def test_knight_outpost_created_when_knight_moves_to_valid_outpost(self) -> None:
        transition = make_transition("7k/8/8/8/4PN2/8/8/K7 w - - 0 1", "f4d5")

        events = KnightOutpostDetector().detect(transition)
        created_events = events_of_type(events, "knight_outpost_created")

        self.assertEqual(len(created_events), 1)
        event = created_events[0]
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.position.fen(), transition.after_position.fen())
        self.assertEqual(event.squares, (chess.D5,))
        self.assertEqual(event.severity, 1.0)
        assert_event_metadata(self, event, transition)

    def test_created_event_evidence_contains_outpost_facts(self) -> None:
        transition = make_transition("7k/8/8/8/4PN2/8/8/K7 w - - 0 1", "f4d5")

        event = events_of_type(
            KnightOutpostDetector().detect(transition),
            "knight_outpost_created",
        )[0]

        self.assertEqual(event.evidence["knight_square"], "d5")
        self.assertEqual(event.evidence["knight_color"], "white")
        self.assertEqual(event.evidence["defending_pawn_squares"], ("e4",))
        self.assertEqual(event.evidence["enemy_pawn_attack_squares"], ())
        self.assertEqual(event.evidence["before_outpost_squares"], ())
        self.assertEqual(event.evidence["after_outpost_squares"], ("d5",))
        self.assertEqual(event.evidence["outpost_move_uci"], "f4d5")
        self.assertEqual(event.evidence["outpost_move_san"], "Nd5")
        self.assertIsNone(event.candidate_move)
        assert_event_metadata(self, event, transition)
        self.assertTrue(
            {"move_uci", "move_san", "before_fen", "after_fen"}.isdisjoint(event.evidence)
        )

    def test_knight_outpost_missed_when_player_had_legal_outpost_move(self) -> None:
        transition = make_transition("7k/8/8/8/4PN2/8/8/K7 w - - 0 1", "a1a2")

        missed_events = events_of_type(
            KnightOutpostDetector().detect(transition),
            "knight_outpost_missed",
        )

        self.assertEqual(len(missed_events), 1)
        event = missed_events[0]
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.position.fen(), transition.before_position.fen())
        self.assertEqual(event.squares, (chess.D5,))
        assert_event_metadata(self, event, transition)
        self.assertEqual(event.evidence["knight_square"], "d5")
        self.assertEqual(event.evidence["defending_pawn_squares"], ("e4",))
        self.assertEqual(event.evidence["outpost_move_uci"], "f4d5")
        self.assertEqual(event.evidence["outpost_move_san"], "Nd5")
        self.assertIsInstance(event.candidate_move, CandidateMove)
        self.assertEqual(event.candidate_move.move_uci, "f4d5")
        self.assertEqual(event.candidate_move.move_san, "Nd5")
        self.assertEqual(event.candidate_move.start_fen, transition.before_position.fen())
        self.assertEqual(event.candidate_move.side, transition.before_position.turn)

    def test_no_outpost_when_knight_is_not_defended_by_friendly_pawn(self) -> None:
        transition = make_transition("7k/8/8/8/5N2/8/8/K7 w - - 0 1", "f4d5")

        events = KnightOutpostDetector().detect(transition)

        self.assertEqual(events, [])

    def test_no_outpost_when_knight_is_attacked_by_enemy_pawn(self) -> None:
        transition = make_transition("7k/8/4p3/8/4PN2/8/8/K7 w - - 0 1", "f4d5")

        events = KnightOutpostDetector().detect(transition)

        self.assertEqual(events, [])

    def test_detect_returns_list_of_detected_events(self) -> None:
        transition = make_transition("7k/8/8/8/4PN2/8/8/K7 w - - 0 1", "f4d5")

        events = KnightOutpostDetector().detect(transition)

        self.assertIsInstance(events, list)
        self.assertTrue(all(isinstance(event, DetectedEvent) for event in events))

    def test_events_contain_no_coaching_language(self) -> None:
        transition = make_transition("7k/8/8/8/4PN2/8/8/K7 w - - 0 1", "f4d5")
        event = events_of_type(
            KnightOutpostDetector().detect(transition),
            "knight_outpost_created",
        )[0]
        event_fields = {field.name for field in fields(DetectedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(event_fields.isdisjoint(forbidden_names))
        self.assertTrue(set(event.evidence).isdisjoint(forbidden_names))

    def test_evidence_contains_structured_machine_facts(self) -> None:
        transition = make_transition("7k/8/8/8/4PN2/8/8/K7 w - - 0 1", "f4d5")

        event = events_of_type(
            KnightOutpostDetector().detect(transition),
            "knight_outpost_created",
        )[0]

        self.assertEqual(event.evidence["knight_square"], "d5")
        self.assertEqual(event.evidence["knight_color"], "white")
        self.assertEqual(event.evidence["defending_pawn_squares"], ("e4",))
        self.assertEqual(event.evidence["enemy_pawn_attack_squares"], ())
        assert_event_metadata(self, event, transition)
        self.assertTrue(
            {"move_uci", "move_san", "before_fen", "after_fen"}.isdisjoint(event.evidence)
        )

    def test_detector_uses_feature_store_defender_and_attack_maps(self) -> None:
        transition = make_transition(chess.STARTING_FEN, "e2e4")
        store = Mock()
        store.defender_map.return_value = {}
        store.attack_map.return_value = {}

        with patch(
            "ai_chess_coach.detectors.knight_outpost_detector.FeatureStore",
            return_value=store,
        ):
            events = KnightOutpostDetector().detect(transition)

        self.assertEqual(events, [])
        self.assertGreater(store.defender_map.call_count, 0)
        self.assertGreater(store.attack_map.call_count, 0)

    def test_detector_source_does_not_call_stockfish_engine_or_llms(self) -> None:
        source = inspect.getsource(knight_outpost_detector).lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("engine", source)

    def test_knight_outpost_detector_is_exported_from_detectors_package(self) -> None:
        import ai_chess_coach.detectors as detectors

        self.assertIs(detectors.KnightOutpostDetector, KnightOutpostDetector)
