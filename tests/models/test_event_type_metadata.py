import unittest
from dataclasses import FrozenInstanceError

from ai_chess_coach.models import (
    EventTypeMetadata,
    VerificationKind,
    get_event_type_metadata,
    registered_event_type_metadata,
)

EXPECTED_METADATA = {
    "hanging_piece_created": (
        "Hanging Piece Created",
        "piece_safety",
        "negative",
        "actual_move",
        False,
    ),
    "hanging_piece_ignored": (
        "Hanging Piece Ignored",
        "piece_safety",
        "negative",
        "actual_move",
        False,
    ),
    "hanging_piece_lost": (
        "Hanging Piece Lost",
        "piece_safety",
        "negative",
        "actual_move",
        False,
    ),
    "fork_created": ("Fork Created", "tactics", "positive", "actual_move", True),
    "fork_missed": ("Fork Missed", "tactics", "negative", "missed_candidate", False),
    "fork_allowed": ("Fork Allowed", "tactics", "negative", "allowed_response", False),
    "knight_outpost_created": (
        "Knight Outpost Created",
        "positional",
        "positive",
        "actual_move",
        True,
    ),
    "knight_outpost_missed": (
        "Knight Outpost Missed",
        "positional",
        "negative",
        "missed_candidate",
        False,
    ),
}


class EventTypeMetadataTest(unittest.TestCase):
    def test_can_be_constructed_with_all_fields(self) -> None:
        metadata = EventTypeMetadata(
            event_type="fork_created",
            display_name="Fork Created",
            category="tactics",
            polarity="positive",
            verification_kind="actual_move",
            is_execution_strength=True,
        )

        self.assertEqual(metadata.event_type, "fork_created")
        self.assertEqual(metadata.display_name, "Fork Created")
        self.assertEqual(metadata.category, "tactics")
        self.assertEqual(metadata.polarity, "positive")
        self.assertEqual(metadata.verification_kind, "actual_move")
        self.assertTrue(metadata.is_execution_strength)

    def test_model_is_frozen(self) -> None:
        metadata = EventTypeMetadata(
            event_type="fork_created",
            display_name="Fork Created",
            category="tactics",
            polarity="positive",
        )

        with self.assertRaises(FrozenInstanceError):
            metadata.polarity = "negative"  # type: ignore[misc]

    def test_model_and_lookup_functions_are_exported(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.EventTypeMetadata, EventTypeMetadata)
        self.assertIs(models.get_event_type_metadata, get_event_type_metadata)
        self.assertIs(models.registered_event_type_metadata, registered_event_type_metadata)
        self.assertTrue(hasattr(models, "EventPolarity"))
        self.assertTrue(hasattr(models, "VerificationKind"))

    def test_all_current_event_types_are_registered(self) -> None:
        registered_event_types = {
            metadata.event_type for metadata in registered_event_type_metadata()
        }

        self.assertEqual(registered_event_types, set(EXPECTED_METADATA))

    def test_registered_metadata_has_expected_values(self) -> None:
        for event_type, (
            display_name,
            category,
            polarity,
            verification_kind,
            is_execution_strength,
        ) in EXPECTED_METADATA.items():
            with self.subTest(event_type=event_type):
                metadata = get_event_type_metadata(event_type)

                self.assertEqual(metadata.event_type, event_type)
                self.assertEqual(metadata.display_name, display_name)
                self.assertEqual(metadata.category, category)
                self.assertEqual(metadata.polarity, polarity)
                self.assertEqual(metadata.verification_kind, verification_kind)
                self.assertEqual(metadata.is_execution_strength, is_execution_strength)

    def test_registered_metadata_is_returned_sorted_by_event_type(self) -> None:
        event_types = [
            metadata.event_type for metadata in registered_event_type_metadata()
        ]

        self.assertEqual(event_types, sorted(event_types))

    def test_unknown_event_type_returns_neutral_metadata(self) -> None:
        metadata = get_event_type_metadata("time_pressure_pattern")

        self.assertEqual(metadata.event_type, "time_pressure_pattern")
        self.assertEqual(metadata.display_name, "Time Pressure Pattern")
        self.assertEqual(metadata.category, "unknown")
        self.assertEqual(metadata.polarity, "neutral")
        self.assertEqual(metadata.verification_kind, "actual_move")
        self.assertFalse(metadata.is_execution_strength)

    def test_verification_kind_type_is_exported(self) -> None:
        self.assertIsNotNone(VerificationKind)
