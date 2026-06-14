import unittest
from dataclasses import FrozenInstanceError, fields

from ai_chess_coach.models import EventMetadata


class EventMetadataTest(unittest.TestCase):
    def test_can_be_constructed_with_all_fields(self) -> None:
        metadata = EventMetadata(
            before_fen="before",
            after_fen="after",
            move_uci="e2e4",
            move_san="e4",
            ply=1,
        )

        self.assertEqual(metadata.before_fen, "before")
        self.assertEqual(metadata.after_fen, "after")
        self.assertEqual(metadata.move_uci, "e2e4")
        self.assertEqual(metadata.move_san, "e4")
        self.assertEqual(metadata.ply, 1)

    def test_model_is_frozen(self) -> None:
        metadata = EventMetadata(
            before_fen="before",
            after_fen="after",
            move_uci="e2e4",
            move_san="e4",
            ply=1,
        )

        with self.assertRaises(FrozenInstanceError):
            metadata.ply = 2  # type: ignore[misc]

    def test_model_has_expected_field_names(self) -> None:
        self.assertEqual(
            [field.name for field in fields(EventMetadata)],
            ["before_fen", "after_fen", "move_uci", "move_san", "ply"],
        )

    def test_event_metadata_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.EventMetadata, EventMetadata)
