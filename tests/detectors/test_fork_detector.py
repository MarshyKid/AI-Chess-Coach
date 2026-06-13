import inspect
import unittest
from dataclasses import fields
from unittest.mock import Mock, patch

import chess

import ai_chess_coach.detectors.fork_detector as fork_detector
from ai_chess_coach.detectors import BaseDetector, ForkDetector
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


def events_of_type(events: list[DetectedEvent], event_type: str) -> list[DetectedEvent]:
    return [event for event in events if event.event_type == event_type]


class ForkDetectorTest(unittest.TestCase):
    def test_detector_inherits_base_detector(self) -> None:
        self.assertIsInstance(ForkDetector(), BaseDetector)

    def test_no_events_when_no_fork_exists(self) -> None:
        transition = make_transition(chess.STARTING_FEN, "e2e4")

        events = ForkDetector().detect(transition)

        self.assertEqual(events, [])

    def test_fork_created_when_move_creates_fork(self) -> None:
        transition = make_transition("8/8/8/4k3/5q2/8/5N2/K7 w - - 0 1", "f2d3")

        events = ForkDetector().detect(transition)
        created_events = events_of_type(events, "fork_created")

        self.assertEqual(len(created_events), 1)
        event = created_events[0]
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.position.fen(), transition.after_position.fen())
        self.assertEqual(event.squares, (chess.D3,))
        self.assertEqual(event.severity, 1.0)

    def test_fork_created_evidence_includes_forking_piece_and_targets(self) -> None:
        transition = make_transition("8/8/8/4k3/5q2/8/5N2/K7 w - - 0 1", "f2d3")

        event = events_of_type(ForkDetector().detect(transition), "fork_created")[0]

        self.assertEqual(event.evidence["forking_piece_square"], "d3")
        self.assertEqual(event.evidence["forking_piece"], "N")
        self.assertEqual(event.evidence["forking_piece_color"], "white")
        self.assertEqual(event.evidence["target_squares"], ("f4", "e5"))
        self.assertEqual(event.evidence["target_pieces"], ("q", "k"))
        self.assertEqual(event.evidence["forking_move_uci"], "f2d3")
        self.assertEqual(event.evidence["forking_move_san"], "Nd3+")
        self.assertEqual(event.evidence["move_uci"], "f2d3")
        self.assertEqual(event.evidence["move_san"], "Nd3+")
        self.assertEqual(event.evidence["before_fen"], transition.before_position.fen())
        self.assertEqual(event.evidence["after_fen"], transition.after_position.fen())

    def test_fork_missed_when_player_had_legal_fork_but_chose_another_move(self) -> None:
        transition = make_transition("8/8/8/4k3/5q2/8/5N2/K7 w - - 0 1", "a1a2")

        missed_events = events_of_type(ForkDetector().detect(transition), "fork_missed")

        self.assertEqual(len(missed_events), 1)
        event = missed_events[0]
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.position.fen(), transition.before_position.fen())
        self.assertEqual(event.squares, (chess.D3,))
        self.assertEqual(event.evidence["forking_move_uci"], "f2d3")
        self.assertEqual(event.evidence["target_squares"], ("f4", "e5"))

    def test_fork_allowed_when_move_gives_opponent_new_fork_opportunity(self) -> None:
        transition = make_transition("7k/8/8/8/5n2/8/1K6/5Q2 w - - 0 1", "f1f2")

        allowed_events = events_of_type(ForkDetector().detect(transition), "fork_allowed")

        self.assertEqual(len(allowed_events), 1)
        event = allowed_events[0]
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.position.fen(), transition.after_position.fen())
        self.assertEqual(event.squares, (chess.D3,))
        self.assertEqual(event.evidence["forking_piece"], "n")
        self.assertEqual(event.evidence["forking_move_uci"], "f4d3")
        self.assertEqual(event.evidence["forking_move_san"], "Nd3+")
        self.assertEqual(event.evidence["target_squares"], ("b2", "f2"))
        self.assertEqual(event.evidence["target_pieces"], ("K", "Q"))

    def test_pawns_are_not_counted_as_valuable_fork_targets(self) -> None:
        transition = make_transition("7k/8/8/4p3/5p2/8/5N2/K7 w - - 0 1", "f2d3")

        events = ForkDetector().detect(transition)

        self.assertEqual(events, [])

    def test_detect_returns_list_of_detected_events(self) -> None:
        transition = make_transition("8/8/8/4k3/5q2/8/5N2/K7 w - - 0 1", "f2d3")

        events = ForkDetector().detect(transition)

        self.assertIsInstance(events, list)
        self.assertTrue(all(isinstance(event, DetectedEvent) for event in events))

    def test_events_contain_no_coaching_language(self) -> None:
        transition = make_transition("8/8/8/4k3/5q2/8/5N2/K7 w - - 0 1", "f2d3")
        event = events_of_type(ForkDetector().detect(transition), "fork_created")[0]
        event_fields = {field.name for field in fields(DetectedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(event_fields.isdisjoint(forbidden_names))
        self.assertTrue(set(event.evidence).isdisjoint(forbidden_names))

    def test_evidence_contains_structured_machine_facts(self) -> None:
        transition = make_transition("8/8/8/4k3/5q2/8/5N2/K7 w - - 0 1", "f2d3")

        event = events_of_type(ForkDetector().detect(transition), "fork_created")[0]

        self.assertEqual(event.evidence["forking_piece_square"], "d3")
        self.assertEqual(event.evidence["target_squares"], ("f4", "e5"))
        self.assertEqual(event.evidence["target_pieces"], ("q", "k"))
        self.assertEqual(event.evidence["before_fen"], transition.before_position.fen())
        self.assertEqual(event.evidence["after_fen"], transition.after_position.fen())

    def test_detector_uses_feature_store_attack_map(self) -> None:
        transition = make_transition(chess.STARTING_FEN, "e2e4")
        store = Mock()
        store.attack_map.return_value = {}

        with patch("ai_chess_coach.detectors.fork_detector.FeatureStore", return_value=store):
            events = ForkDetector().detect(transition)

        self.assertEqual(events, [])
        self.assertGreater(store.attack_map.call_count, 0)

    def test_detector_source_does_not_call_stockfish_engine_llms_or_board_attackers(self) -> None:
        source = inspect.getsource(fork_detector).lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("engine", source)
        self.assertNotIn(".attackers(", source)

    def test_fork_detector_is_exported_from_detectors_package(self) -> None:
        import ai_chess_coach.detectors as detectors

        self.assertIs(detectors.ForkDetector, ForkDetector)
        self.assertFalse(hasattr(detectors, "EngineVerificationDetector"))
