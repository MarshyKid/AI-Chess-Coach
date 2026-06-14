import unittest
from dataclasses import fields

import chess

from ai_chess_coach.models import DetectedEvent, EventMetadata


class DetectedEventTest(unittest.TestCase):
    def test_can_be_constructed_with_typed_metadata_and_evidence(self) -> None:
        metadata = EventMetadata(
            before_fen=chess.STARTING_FEN,
            after_fen=chess.Board().fen(),
            move_uci="e2e4",
            move_san="e4",
            ply=1,
        )
        event = DetectedEvent(
            event_type="hanging_piece_created",
            side=chess.WHITE,
            move=chess.Move.from_uci("e2e4"),
            position=chess.Board(),
            squares=(chess.E4,),
            metadata=metadata,
            evidence={"piece_square": "e4"},
            severity=1.0,
        )

        self.assertIs(event.metadata, metadata)
        self.assertEqual(event.evidence["piece_square"], "e4")

    def test_detected_event_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(DetectedEvent)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_detected_event_includes_metadata_field(self) -> None:
        field_names = {field.name for field in fields(DetectedEvent)}

        self.assertIn("metadata", field_names)
