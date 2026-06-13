import unittest
from dataclasses import FrozenInstanceError, fields

from ai_chess_coach.models import DetectedPattern, WeaknessProfile


def make_pattern(pattern_type: str = "hanging_piece_created") -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pattern_type,
        frequency=2,
        severity=50.0,
        supporting_events=(),
    )


class WeaknessProfileTest(unittest.TestCase):
    def test_can_be_constructed_with_strengths_weaknesses_and_recurring_themes(self) -> None:
        strength = make_pattern("knight_outpost_created")
        weakness = make_pattern("hanging_piece_created")
        neutral = make_pattern("neutral_pattern")

        profile = WeaknessProfile(
            strengths=(strength,),
            weaknesses=(weakness,),
            recurring_themes=(strength, weakness, neutral),
        )

        self.assertEqual(profile.strengths, (strength,))
        self.assertEqual(profile.weaknesses, (weakness,))
        self.assertEqual(profile.recurring_themes, (strength, weakness, neutral))

    def test_model_is_frozen(self) -> None:
        profile = WeaknessProfile(
            strengths=(),
            weaknesses=(make_pattern(),),
            recurring_themes=(make_pattern(),),
        )

        with self.assertRaises(FrozenInstanceError):
            profile.weaknesses = ()  # type: ignore[misc]

    def test_model_has_no_coaching_language_fields(self) -> None:
        field_names = {field.name for field in fields(WeaknessProfile)}
        forbidden_names = {"message", "explanation", "recommendation", "advice"}

        self.assertTrue(field_names.isdisjoint(forbidden_names))

    def test_weakness_profile_is_exported_from_models_package(self) -> None:
        import ai_chess_coach.models as models

        self.assertIs(models.WeaknessProfile, WeaknessProfile)
