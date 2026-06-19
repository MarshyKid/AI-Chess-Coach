import os
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_chess_coach.coaching import LLMClient, LLMPrompt
from ai_chess_coach.coaching.providers import (
    DEFAULT_OPENAI_MODEL,
    OPENAI_API_KEY_ENV_VAR,
    OPENAI_MODEL_ENV_VAR,
    EmptyLLMResponseError,
    LLMProviderError,
    MissingLLMApiKeyError,
    MissingLLMProviderDependencyError,
    OpenAILLMClient,
)


class FakeOpenAIResponse:
    def __init__(self, output_text: object) -> None:
        self.output_text = output_text


class FakeResponses:
    def __init__(
        self,
        output_text: object = "grounded answer",
        *,
        error: Exception | None = None,
    ) -> None:
        self.output_text = output_text
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> FakeOpenAIResponse:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error

        return FakeOpenAIResponse(self.output_text)


class FakeOpenAIClient:
    def __init__(
        self,
        output_text: object = "grounded answer",
        *,
        error: Exception | None = None,
    ) -> None:
        self.responses = FakeResponses(output_text, error=error)


class OpenAILLMClientTest(unittest.TestCase):
    def test_openai_client_satisfies_llm_client_protocol(self) -> None:
        client = OpenAILLMClient(client=FakeOpenAIClient())

        self.assertIsInstance(client, LLMClient)

    def test_generate_preserves_system_and_user_prompt_separation(self) -> None:
        fake_provider = FakeOpenAIClient(output_text="coach response")
        client = OpenAILLMClient(client=fake_provider, model="test-model")

        response = client.generate(
            LLMPrompt(system="system grounding", user="user evidence")
        )

        self.assertEqual(response, "coach response")
        self.assertEqual(
            fake_provider.responses.calls,
            [
                {
                    "model": "test-model",
                    "instructions": "system grounding",
                    "input": "user evidence",
                }
            ],
        )

    def test_injected_client_needs_no_api_key_or_sdk_import(self) -> None:
        fake_provider = FakeOpenAIClient()

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "ai_chess_coach.coaching.providers.openai_client._create_openai_client",
                side_effect=AssertionError("SDK factory should not be called"),
            ):
                client = OpenAILLMClient(client=fake_provider)

        self.assertEqual(
            client.generate(LLMPrompt(system="system", user="user")),
            "grounded answer",
        )

    def test_model_resolution_prefers_constructor_then_env_then_default(self) -> None:
        with patch.dict(
            os.environ,
            {OPENAI_MODEL_ENV_VAR: "env-model"},
            clear=True,
        ):
            env_fake = FakeOpenAIClient()
            OpenAILLMClient(client=env_fake).generate(
                LLMPrompt(system="system", user="user")
            )
            explicit_fake = FakeOpenAIClient()
            OpenAILLMClient(client=explicit_fake, model=" explicit-model ").generate(
                LLMPrompt(system="system", user="user")
            )

        with patch.dict(os.environ, {}, clear=True):
            default_fake = FakeOpenAIClient()
            OpenAILLMClient(client=default_fake).generate(
                LLMPrompt(system="system", user="user")
            )

        self.assertEqual(env_fake.responses.calls[0]["model"], "env-model")
        self.assertEqual(explicit_fake.responses.calls[0]["model"], "explicit-model")
        self.assertEqual(default_fake.responses.calls[0]["model"], DEFAULT_OPENAI_MODEL)

    def test_api_key_resolution_prefers_constructor_then_env(self) -> None:
        created_keys: list[str] = []

        def fake_create(api_key: str) -> FakeOpenAIClient:
            created_keys.append(api_key)
            return FakeOpenAIClient()

        with patch(
            "ai_chess_coach.coaching.providers.openai_client._create_openai_client",
            side_effect=fake_create,
        ):
            with patch.dict(os.environ, {OPENAI_API_KEY_ENV_VAR: "env-key"}, clear=True):
                OpenAILLMClient()
                OpenAILLMClient(api_key=" explicit-key ")

        self.assertEqual(created_keys, ["env-key", "explicit-key"])

    def test_missing_api_key_raises_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(MissingLLMApiKeyError):
                OpenAILLMClient()

    def test_missing_provider_dependency_is_exposed(self) -> None:
        with patch(
            "ai_chess_coach.coaching.providers.openai_client._create_openai_client",
            side_effect=MissingLLMProviderDependencyError("install optional extra"),
        ):
            with patch.dict(os.environ, {OPENAI_API_KEY_ENV_VAR: "env-key"}, clear=True):
                with self.assertRaises(MissingLLMProviderDependencyError):
                    OpenAILLMClient()

    def test_provider_exception_is_wrapped(self) -> None:
        client = OpenAILLMClient(
            client=FakeOpenAIClient(error=RuntimeError("provider exploded"))
        )

        with self.assertRaises(LLMProviderError) as context:
            client.generate(LLMPrompt(system="system", user="user"))

        self.assertIsInstance(context.exception.__cause__, RuntimeError)

    def test_empty_or_invalid_output_text_raises_clear_error(self) -> None:
        for output_text in ("", "   ", None, 42):
            with self.subTest(output_text=output_text):
                client = OpenAILLMClient(client=FakeOpenAIClient(output_text))

                with self.assertRaises(EmptyLLMResponseError):
                    client.generate(LLMPrompt(system="system", user="user"))

    def test_provider_is_exported_only_from_provider_package(self) -> None:
        import ai_chess_coach.coaching as coaching
        import ai_chess_coach.coaching.providers as providers

        self.assertIs(providers.OpenAILLMClient, OpenAILLMClient)
        self.assertFalse(hasattr(coaching, "OpenAILLMClient"))

    def test_openai_extra_is_declared_optional(self) -> None:
        pyproject = (
            Path(__file__).parents[2] / "pyproject.toml"
        ).read_text(encoding="utf-8")

        self.assertIn("[project.optional-dependencies]", pyproject)
        self.assertIn('openai = [', pyproject)
        self.assertIn('"openai>=2.0.0,<3"', pyproject)

    def test_provider_source_has_no_forbidden_runtime_dependencies(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "providers"
            / "openai_client.py"
        ).read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("stockfish", lower_source)
        self.assertNotIn("ai_chess_coach.engine", lower_source)
        self.assertNotIn("ai_chess_coach.detectors", lower_source)
        self.assertNotIn("featurestore", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("chess.board", lower_source)
        self.assertNotIn("board.attackers", source)
        self.assertNotIn("Board.attackers", source)
        self.assertNotIn("ai_chess_coach.retrieval", lower_source)
        self.assertNotIn("ai_chess_coach.cli", lower_source)
        self.assertNotIn("requests", lower_source)
        self.assertNotIn("httpx", lower_source)
        self.assertNotIn("socket", lower_source)
        self.assertNotIn("anthropic", lower_source)
        self.assertNotIn("gemini", lower_source)
