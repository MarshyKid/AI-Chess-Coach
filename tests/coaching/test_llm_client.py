import dataclasses
from pathlib import Path
import unittest

from ai_chess_coach.coaching import LLMClient, LLMPrompt


class RecordingLLMClient:
    """A fake provider-agnostic client that records the prompt it receives."""

    def __init__(self, response: str = "coaching response") -> None:
        self.response = response
        self.received: LLMPrompt | None = None

    def generate(self, prompt: LLMPrompt) -> str:
        self.received = prompt
        return self.response


class LLMPromptTest(unittest.TestCase):
    def test_prompt_holds_system_and_user_sections(self) -> None:
        prompt = LLMPrompt(system="rules", user="question")

        self.assertEqual(prompt.system, "rules")
        self.assertEqual(prompt.user, "question")

    def test_prompt_is_immutable(self) -> None:
        prompt = LLMPrompt(system="rules", user="question")

        with self.assertRaises(dataclasses.FrozenInstanceError):
            prompt.user = "changed"  # type: ignore[misc]


class LLMClientProtocolTest(unittest.TestCase):
    def test_fake_satisfies_protocol_at_runtime(self) -> None:
        self.assertIsInstance(RecordingLLMClient(), LLMClient)

    def test_object_without_generate_is_not_a_client(self) -> None:
        self.assertNotIn(LLMClient.__name__, (type(object()).__name__,))
        self.assertNotIsInstance(object(), LLMClient)

    def test_generate_receives_prompt_and_returns_text(self) -> None:
        client = RecordingLLMClient("here is your review")
        prompt = LLMPrompt(system="rules", user="why did I hang my bishop?")

        response = client.generate(prompt)

        self.assertEqual(response, "here is your review")
        self.assertIs(client.received, prompt)


class LLMClientBoundaryTest(unittest.TestCase):
    def test_module_does_not_import_engine_or_provider_sdks(self) -> None:
        source = _module_source("llm_client.py")
        for forbidden in _FORBIDDEN_IMPORTS:
            self.assertNotIn(forbidden, source, forbidden)


_FORBIDDEN_IMPORTS = (
    "stockfish",
    "ai_chess_coach.engine",
    "ai_chess_coach.detectors",
    "featurestore",
    "legal_moves",
    "attackers",
    "anthropic",
    "openai",
    "gemini",
    "requests",
    "httpx",
)


def _module_source(file_name: str) -> str:
    path = (
        Path(__file__).parents[2]
        / "src"
        / "ai_chess_coach"
        / "coaching"
        / file_name
    )
    return path.read_text(encoding="utf-8").lower()


if __name__ == "__main__":
    unittest.main()
