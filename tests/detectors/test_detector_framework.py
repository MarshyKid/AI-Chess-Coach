import unittest
from dataclasses import fields

import chess

from ai_chess_coach.detectors import BaseDetector, DetectionPipeline, DetectorRegistry
from ai_chess_coach.models import DetectedEvent, MoveTransition


def make_transition() -> MoveTransition:
    before = chess.Board()
    move = chess.Move.from_uci("e2e4")
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


def make_event(event_type: str, transition: MoveTransition) -> DetectedEvent:
    return DetectedEvent(
        event_type=event_type,
        side=chess.WHITE,
        move=transition.move,
        position=transition.after_position,
        squares=(chess.E4,),
        evidence={
            "piece_square": "e4",
            "attackers": (),
            "defenders": ("e1",),
        },
        severity=0.5,
    )


class RecordingDetector(BaseDetector):
    def __init__(self, event_types: tuple[str, ...]) -> None:
        self.event_types = event_types
        self.transitions: list[MoveTransition] = []

    def detect(self, transition: MoveTransition) -> list[DetectedEvent]:
        self.transitions.append(transition)
        return [make_event(event_type, transition) for event_type in self.event_types]


class DetectorFrameworkTest(unittest.TestCase):
    def test_concrete_detector_can_inherit_base_detector(self) -> None:
        detector = RecordingDetector(())

        self.assertIsInstance(detector, BaseDetector)

    def test_detect_returns_list_of_detected_events(self) -> None:
        transition = make_transition()
        detector = RecordingDetector(("fake_event",))

        events = detector.detect(transition)

        self.assertIsInstance(events, list)
        self.assertTrue(all(isinstance(event, DetectedEvent) for event in events))

    def test_registry_can_register_one_detector(self) -> None:
        registry = DetectorRegistry()
        detector = RecordingDetector(())

        registry.register(detector)

        self.assertEqual(registry.registered_detectors(), (detector,))

    def test_registry_can_register_multiple_detectors_in_order(self) -> None:
        registry = DetectorRegistry()
        first = RecordingDetector(("first_event",))
        second = RecordingDetector(("second_event",))

        registry.register(first)
        registry.register(second)

        self.assertEqual(registry.registered_detectors(), (first, second))

    def test_registry_rejects_non_detector_objects(self) -> None:
        registry = DetectorRegistry()

        with self.assertRaises(TypeError):
            registry.register(object())  # type: ignore[arg-type]

    def test_pipeline_runs_all_registered_detectors(self) -> None:
        transition = make_transition()
        registry = DetectorRegistry()
        first = RecordingDetector(("first_event",))
        second = RecordingDetector(("second_event",))
        registry.register(first)
        registry.register(second)

        DetectionPipeline(registry).run(transition)

        self.assertEqual(first.transitions, [transition])
        self.assertEqual(second.transitions, [transition])

    def test_pipeline_combines_events_from_multiple_detectors(self) -> None:
        transition = make_transition()
        registry = DetectorRegistry()
        registry.register(RecordingDetector(("first_event",)))
        registry.register(RecordingDetector(("second_event", "third_event")))

        events = DetectionPipeline(registry).run(transition)

        self.assertEqual([event.event_type for event in events], ["first_event", "second_event", "third_event"])
        self.assertTrue(all(isinstance(event, DetectedEvent) for event in events))

    def test_detected_event_can_be_created_with_structured_evidence(self) -> None:
        transition = make_transition()

        event = make_event("structured_event", transition)

        self.assertEqual(event.event_type, "structured_event")
        self.assertEqual(event.side, chess.WHITE)
        self.assertEqual(event.move, transition.move)
        self.assertIs(event.position, transition.after_position)
        self.assertEqual(event.squares, (chess.E4,))
        self.assertEqual(event.evidence["piece_square"], "e4")
        self.assertEqual(event.severity, 0.5)

    def test_detected_event_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(DetectedEvent)}

        self.assertNotIn("message", field_names)
        self.assertNotIn("explanation", field_names)
        self.assertNotIn("recommendation", field_names)
        self.assertNotIn("advice", field_names)

    def test_future_chess_detector_modules_are_not_exposed(self) -> None:
        import ai_chess_coach.detectors as detectors

        self.assertFalse(hasattr(detectors, "ForkDetector"))
        self.assertFalse(hasattr(detectors, "KnightOutpostDetector"))
