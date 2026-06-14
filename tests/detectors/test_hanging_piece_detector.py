import inspect
import unittest
from dataclasses import fields
from unittest.mock import Mock, patch

import chess

import ai_chess_coach.detectors.hanging_piece_detector as hanging_piece_detector
from ai_chess_coach.detectors import BaseDetector, HangingPieceDetector
from ai_chess_coach.models import DetectedEvent, MoveTransition


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


class HangingPieceDetectorTest(unittest.TestCase):
    def test_detector_inherits_base_detector(self) -> None:
        self.assertIsInstance(HangingPieceDetector(), BaseDetector)

    def test_no_events_when_no_hanging_pieces_before_or_after(self) -> None:
        transition = make_transition(chess.STARTING_FEN, "e2e4")

        events = HangingPieceDetector().detect(transition)

        self.assertEqual(events, [])

    def test_hanging_piece_created_when_move_leaves_piece_hanging(self) -> None:
        transition = make_transition("3r3k/8/8/8/8/8/4B3/4K3 w - - 0 1", "e2d3")

        events = HangingPieceDetector().detect(transition)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.event_type, "hanging_piece_created")
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.squares, (chess.D3,))
        self.assertEqual(event.position.fen(), transition.after_position.fen())
        self.assertEqual(event.severity, 1.0)
        assert_event_metadata(self, event, transition)
        self.assertEqual(event.evidence["piece_square"], "d3")
        self.assertEqual(event.evidence["piece"], "B")
        self.assertEqual(event.evidence["piece_color"], "white")
        self.assertEqual(event.evidence["attackers"], ("d8",))
        self.assertEqual(event.evidence["defenders"], ())
        self.assertEqual(event.evidence["before_hanging_squares"], ())
        self.assertEqual(event.evidence["after_hanging_squares"], ("d3",))

    def test_hanging_piece_ignored_when_opponent_hanging_piece_remains(self) -> None:
        transition = make_transition("7k/8/8/8/3n4/8/8/3RK3 w - - 0 1", "e1f1")

        events = HangingPieceDetector().detect(transition)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.event_type, "hanging_piece_ignored")
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.squares, (chess.D4,))
        self.assertEqual(event.position.fen(), transition.before_position.fen())
        assert_event_metadata(self, event, transition)
        self.assertEqual(event.evidence["piece_square"], "d4")
        self.assertEqual(event.evidence["piece"], "n")
        self.assertEqual(event.evidence["attackers"], ("d1",))
        self.assertEqual(event.evidence["defenders"], ())
        self.assertEqual(event.evidence["before_hanging_squares"], ("d4",))
        self.assertEqual(event.evidence["after_hanging_squares"], ("d4",))

    def test_hanging_piece_lost_when_hanging_piece_is_captured(self) -> None:
        transition = make_transition("7k/8/8/8/3n4/8/8/3RK3 w - - 0 1", "d1d4")

        events = HangingPieceDetector().detect(transition)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.event_type, "hanging_piece_lost")
        self.assertEqual(event.side, chess.BLACK)
        self.assertEqual(event.squares, (chess.D4,))
        self.assertEqual(event.position.fen(), transition.before_position.fen())
        assert_event_metadata(self, event, transition)
        self.assertEqual(event.evidence["piece_square"], "d4")
        self.assertEqual(event.evidence["piece"], "n")
        self.assertEqual(event.evidence["captured_square"], "d4")
        self.assertEqual(event.evidence["captured_piece"], "n")
        self.assertEqual(event.evidence["before_hanging_squares"], ("d4",))
        self.assertEqual(event.evidence["after_hanging_squares"], ())

    def test_detect_returns_list_of_detected_events(self) -> None:
        transition = make_transition("3r3k/8/8/8/8/8/4B3/4K3 w - - 0 1", "e2d3")

        events = HangingPieceDetector().detect(transition)

        self.assertIsInstance(events, list)
        self.assertTrue(all(isinstance(event, DetectedEvent) for event in events))

    def test_events_contain_no_coaching_language(self) -> None:
        transition = make_transition("3r3k/8/8/8/8/8/4B3/4K3 w - - 0 1", "e2d3")
        event = HangingPieceDetector().detect(transition)[0]
        event_fields = {field.name for field in fields(DetectedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(event_fields.isdisjoint(forbidden_names))
        self.assertTrue(set(event.evidence).isdisjoint(forbidden_names))

    def test_evidence_contains_structured_machine_facts(self) -> None:
        transition = make_transition("7k/8/8/8/3n4/8/8/3RK3 w - - 0 1", "d1d4")

        event = HangingPieceDetector().detect(transition)[0]

        self.assertEqual(event.evidence["piece_square"], "d4")
        self.assertEqual(event.evidence["piece"], "n")
        self.assertEqual(event.evidence["piece_color"], "black")
        self.assertEqual(event.evidence["attackers"], ("d1",))
        self.assertEqual(event.evidence["defenders"], ())
        assert_event_metadata(self, event, transition)
        self.assertTrue(
            {"move_uci", "move_san", "before_fen", "after_fen"}.isdisjoint(event.evidence)
        )

    def test_detector_uses_feature_store_piece_safety_for_before_and_after(self) -> None:
        transition = make_transition(chess.STARTING_FEN, "e2e4")
        before_store = Mock()
        after_store = Mock()
        before_store.piece_safety.return_value = {}
        after_store.piece_safety.return_value = {}

        with patch(
            "ai_chess_coach.detectors.hanging_piece_detector.FeatureStore",
            side_effect=(before_store, after_store),
        ) as feature_store:
            events = HangingPieceDetector().detect(transition)

        self.assertEqual(events, [])
        self.assertEqual(feature_store.call_count, 2)
        before_store.piece_safety.assert_called_once_with()
        after_store.piece_safety.assert_called_once_with()

    def test_detector_source_does_not_call_stockfish_engine_or_llms(self) -> None:
        source = inspect.getsource(hanging_piece_detector).lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("engine", source)

    def test_hanging_piece_detector_is_exported_from_detectors_package(self) -> None:
        import ai_chess_coach.detectors as detectors

        self.assertIs(detectors.HangingPieceDetector, HangingPieceDetector)
