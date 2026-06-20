import os
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch

from ai_chess_coach.coaching import LLMClient, LLMPrompt
from ai_chess_coach.coaching.providers import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_BASE_URL_ENV_VAR,
    OLLAMA_MODEL_ENV_VAR,
    EmptyLLMResponseError,
    OllamaLLMClient,
    OllamaModelNotFoundError,
    OllamaProviderError,
    OllamaUnavailableError,
)


class FakeOllamaTransport:
    def __init__(
        self,
        response: dict[str, object] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.response = (
            response if response is not None else {"message": {"content": "grounded answer"}}
        )
        self.error = error
        self.calls: list[tuple[str, dict[str, object]]] = []

    def post_json(
        self,
        url: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append((url, payload))
        if self.error is not None:
            raise self.error

        return self.response


class OllamaLLMClientTest(unittest.TestCase):
    def test_ollama_client_satisfies_llm_client_protocol(self) -> None:
        client = OllamaLLMClient(client=FakeOllamaTransport())

        self.assertIsInstance(client, LLMClient)

    def test_generate_preserves_system_and_user_prompt_separation(self) -> None:
        transport = FakeOllamaTransport(
            {"message": {"content": "local response"}}
        )
        client = OllamaLLMClient(
            model="test-model",
            base_url="http://localhost:11434",
            client=transport,
        )

        response = client.generate(
            LLMPrompt(system="system grounding", user="user evidence")
        )

        self.assertEqual(response, "local response")
        self.assertEqual(
            transport.calls,
            [
                (
                    "http://localhost:11434/api/chat",
                    {
                        "model": "test-model",
                        "messages": [
                            {"role": "system", "content": "system grounding"},
                            {"role": "user", "content": "user evidence"},
                        ],
                        "stream": False,
                    },
                )
            ],
        )

    def test_model_resolution_prefers_constructor_then_env_then_default(self) -> None:
        with patch.dict(os.environ, {OLLAMA_MODEL_ENV_VAR: "env-model"}, clear=True):
            env_transport = FakeOllamaTransport()
            OllamaLLMClient(client=env_transport).generate(
                LLMPrompt(system="system", user="user")
            )
            explicit_transport = FakeOllamaTransport()
            OllamaLLMClient(
                model=" explicit-model ",
                client=explicit_transport,
            ).generate(LLMPrompt(system="system", user="user"))

        with patch.dict(os.environ, {}, clear=True):
            default_transport = FakeOllamaTransport()
            OllamaLLMClient(client=default_transport).generate(
                LLMPrompt(system="system", user="user")
            )

        self.assertEqual(env_transport.calls[0][1]["model"], "env-model")
        self.assertEqual(
            explicit_transport.calls[0][1]["model"],
            "explicit-model",
        )
        self.assertEqual(default_transport.calls[0][1]["model"], DEFAULT_OLLAMA_MODEL)

    def test_base_url_resolution_prefers_constructor_then_env_then_default(self) -> None:
        with patch.dict(
            os.environ,
            {OLLAMA_BASE_URL_ENV_VAR: " http://env-host:11434/ "},
            clear=True,
        ):
            env_transport = FakeOllamaTransport()
            OllamaLLMClient(client=env_transport).generate(
                LLMPrompt(system="system", user="user")
            )
            explicit_transport = FakeOllamaTransport()
            OllamaLLMClient(
                base_url=" http://explicit-host:11434/// ",
                client=explicit_transport,
            ).generate(LLMPrompt(system="system", user="user"))

        with patch.dict(os.environ, {}, clear=True):
            default_transport = FakeOllamaTransport()
            OllamaLLMClient(client=default_transport).generate(
                LLMPrompt(system="system", user="user")
            )

        self.assertEqual(env_transport.calls[0][0], "http://env-host:11434/api/chat")
        self.assertEqual(
            explicit_transport.calls[0][0],
            "http://explicit-host:11434/api/chat",
        )
        self.assertEqual(
            default_transport.calls[0][0],
            f"{DEFAULT_OLLAMA_BASE_URL}/api/chat",
        )

    def test_empty_output_text_raises_clear_error(self) -> None:
        for response in (
            {"message": {"content": ""}},
            {"message": {"content": "   "}},
            {"message": {"content": None}},
            {"message": {"content": 42}},
        ):
            with self.subTest(response=response):
                client = OllamaLLMClient(client=FakeOllamaTransport(response))

                with self.assertRaises(EmptyLLMResponseError):
                    client.generate(LLMPrompt(system="system", user="user"))

    def test_malformed_response_raises_clear_error(self) -> None:
        for response in ({}, {"message": "bad"}):
            with self.subTest(response=response):
                client = OllamaLLMClient(client=FakeOllamaTransport(response))

                with self.assertRaises(OllamaProviderError):
                    client.generate(LLMPrompt(system="system", user="user"))

    def test_connection_failure_raises_unavailable_error(self) -> None:
        client = OllamaLLMClient(
            client=FakeOllamaTransport(error=OSError("connection refused"))
        )

        with self.assertRaises(OllamaUnavailableError):
            client.generate(LLMPrompt(system="system", user="user"))

    def test_url_failure_raises_unavailable_error(self) -> None:
        client = OllamaLLMClient(
            client=FakeOllamaTransport(
                error=urllib.error.URLError("connection refused")
            )
        )

        with self.assertRaises(OllamaUnavailableError):
            client.generate(LLMPrompt(system="system", user="user"))

    def test_model_not_found_error_payload_is_represented_clearly(self) -> None:
        client = OllamaLLMClient(
            client=FakeOllamaTransport(
                {"error": "model llama3.2:3b not found, try pulling it"}
            )
        )

        with self.assertRaises(OllamaModelNotFoundError):
            client.generate(LLMPrompt(system="system", user="user"))

    def test_other_error_payload_raises_provider_error(self) -> None:
        client = OllamaLLMClient(
            client=FakeOllamaTransport({"error": "unexpected local failure"})
        )

        with self.assertRaises(OllamaProviderError):
            client.generate(LLMPrompt(system="system", user="user"))

    def test_unexpected_transport_error_is_wrapped(self) -> None:
        client = OllamaLLMClient(
            client=FakeOllamaTransport(error=RuntimeError("boom"))
        )

        with self.assertRaises(OllamaProviderError) as context:
            client.generate(LLMPrompt(system="system", user="user"))

        self.assertIsInstance(context.exception.__cause__, RuntimeError)

    def test_provider_is_exported_only_from_provider_package(self) -> None:
        import ai_chess_coach.coaching as coaching
        import ai_chess_coach.coaching.providers as providers

        self.assertIs(providers.OllamaLLMClient, OllamaLLMClient)
        self.assertFalse(hasattr(coaching, "OllamaLLMClient"))

    def test_provider_source_has_no_forbidden_runtime_dependencies(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "coaching"
            / "providers"
            / "ollama_client.py"
        ).read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("stockfish", lower_source)
        self.assertNotIn("ai_chess_coach.engine", lower_source)
        self.assertNotIn("ai_chess_coach.detectors", lower_source)
        self.assertNotIn("featurestore", lower_source)
        self.assertNotIn("ai_chess_coach.analysis", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("chess.board", lower_source)
        self.assertNotIn("board.attackers", source)
        self.assertNotIn("Board.attackers", source)
        self.assertNotIn("ai_chess_coach.retrieval", lower_source)
        self.assertNotIn("ai_chess_coach.cli", lower_source)
        self.assertNotIn("promptbuilder", lower_source)
        self.assertNotIn("llmchatcoach", lower_source)
        self.assertNotIn("openai", lower_source)
        self.assertNotIn("anthropic", lower_source)
        self.assertNotIn("gemini", lower_source)
        self.assertNotIn("requests", lower_source)
        self.assertNotIn("httpx", lower_source)
        self.assertNotIn("socket", lower_source)
