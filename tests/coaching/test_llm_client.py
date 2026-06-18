import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from ai_chess_coach.coaching import LLMClient, LLMPrompt


class FakeLLMClient:
    def __init__(self) -> None:
        self.received_prompt: LLMPrompt | None = None

    def generate(self, prompt: LLMPrompt) -> str:
        self.received_prompt = prompt
        return f"fake response: {prompt.user}"


class LLMClientTest(unittest.TestCase):
    def test_llm_prompt_stores_system_and_user_messages(self) -> None:
        prompt = LLMPrompt(system="system instructions", user="user evidence")

        self.assertEqual(prompt.system, "system instructions")
        self.assertEqual(prompt.user, "user evidence")

    def test_llm_prompt_is_frozen(self) -> None:
        prompt = LLMPrompt(system="system", user="user")

        with self.assertRaises(FrozenInstanceError):
            prompt.user = "changed"  # type: ignore[misc]

    def test_fake_client_satisfies_protocol_and_receives_prompt(self) -> None:
        client = FakeLLMClient()
        prompt = LLMPrompt(system="system", user="evidence")

        response = client.generate(prompt)

        self.assertIsInstance(client, LLMClient)
        self.assertIs(client.received_prompt, prompt)
        self.assertEqual(response, "fake response: evidence")

    def test_llm_types_are_exported_from_coaching_package(self) -> None:
        import ai_chess_coach.coaching as coaching

        self.assertIs(coaching.LLMClient, LLMClient)
        self.assertIs(coaching.LLMPrompt, LLMPrompt)

    def test_client_boundary_has_no_provider_or_network_dependencies(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "llm_client.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("stockfish", source)
        self.assertNotIn("ai_chess_coach.engine", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("anthropic", source)
        self.assertNotIn("gemini", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("httpx", source)
        self.assertNotIn("socket", source)
