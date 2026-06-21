"""Tests for the local-development FastAPI app."""

from __future__ import annotations

import importlib
from pathlib import Path
import unittest
from unittest.mock import patch

import chess
from fastapi.testclient import TestClient

from ai_chess_coach.coaching import LLMPrompt
from ai_chess_coach.coaching.providers.errors import EmptyLLMResponseError, LLMProviderError
from ai_chess_coach.coaching.providers.ollama_client import (
    OllamaModelNotFoundError,
    OllamaProviderError,
    OllamaUnavailableError,
)
from ai_chess_coach.engine import StockfishUnavailableError
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedEvent,
    DetectedPattern,
    EngineAssessment,
    EngineScore,
    EventMetadata,
    GameAnalysisResult,
    MoveTransition,
    VerifiedEvent,
    WeaknessProfile,
)

api_module = importlib.import_module("ai_chess_coach.api.app")


class RecordingLLMClient:
    def __init__(self, response: str = "grounded api answer") -> None:
        self.response = response
        self.received_prompt: LLMPrompt | None = None

    def generate(self, prompt: LLMPrompt) -> str:
        self.received_prompt = prompt
        return self.response


class RaisingLLMClient:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def generate(self, prompt: LLMPrompt) -> str:
        raise self.exc


class ApiAppTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(api_module.app)

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ok"}, response.json())

    def test_analyze_returns_frontend_friendly_json(self) -> None:
        with patch.object(api_module, "analyze_pgn", return_value=populated_result()):
            response = self.client.post(
                "/analyze",
                json={"pgn": '[Event "Secret raw PGN marker"]\n\n1. e4 *\n'},
            )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual(1, body["moves"])
        self.assertEqual(
            [
                {
                    "title": "Move 1: Piece safety issue",
                    "explanation": "A selected coaching moment was found.",
                    "position_reference": body["coaching_moments"][0]["position_reference"],
                    "highlights": ["e4"],
                    "details": [
                        "hanging_piece_created: white pawn on e4 became hanging; "
                        "attackers: d5; defenders: none"
                    ],
                }
            ],
            body["coaching_moments"],
        )
        self.assertEqual(
            {
                "pattern_type": "hanging_piece_created",
                "display_name": "Hanging Piece Created",
                "frequency": 1,
                "severity": 50.0,
            },
            body["weakness_profile"]["weaknesses"][0],
        )
        self.assertEqual([], body["weakness_profile"]["strengths"])
        self.assertEqual([], body["weakness_profile"]["execution_strengths"])
        self.assertNotIn("Secret raw PGN marker", response.text)
        self.assertNotIn("detected_events", body)
        self.assertNotIn("verified_events", body)
        self.assertNotIn("detected_patterns", body)

    def test_coach_uses_selected_evidence_without_raw_pgn(self) -> None:
        fake_client = RecordingLLMClient(response="study piece safety")
        built_clients: list[tuple[str | None, str | None]] = []

        def fake_build_client(*, model: str | None, base_url: str | None) -> RecordingLLMClient:
            built_clients.append((model, base_url))
            return fake_client

        with (
            patch.object(api_module, "analyze_pgn", return_value=populated_result()),
            patch.object(api_module, "build_ollama_client", side_effect=fake_build_client),
        ):
            response = self.client.post(
                "/coach",
                json={
                    "pgn": '[Event "Secret raw PGN marker"]\n\n1. e4 *\n',
                    "question": "What should I improve?",
                    "model": "qwen2.5:7b",
                    "ollama_base_url": "http://localhost:11434",
                },
            )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("study piece safety", body["answer"])
        self.assertEqual(
            {"coaching_moment_count": 1, "has_weakness_profile": True},
            body["evidence_summary"],
        )
        self.assertEqual("Move 1: Piece safety issue", body["coaching_moments"][0]["title"])
        self.assertEqual([("qwen2.5:7b", "http://localhost:11434")], built_clients)
        self.assertNotIn("Secret raw PGN marker", response.text)
        assert fake_client.received_prompt is not None
        self.assertIn("What should I improve?", fake_client.received_prompt.user)
        self.assertIn("Move 1: Piece safety issue", fake_client.received_prompt.user)
        self.assertIn("Weaknesses: Hanging Piece Created", fake_client.received_prompt.user)
        self.assertNotIn("Secret raw PGN marker", fake_client.received_prompt.user)

    def test_request_validation_rejects_missing_or_blank_values(self) -> None:
        cases = (
            ("post", "/analyze", {}, 422),
            ("post", "/analyze", {"pgn": "   "}, 422),
            ("post", "/coach", {"pgn": "1. e4 *"}, 422),
            ("post", "/coach", {"pgn": "1. e4 *", "question": "   "}, 422),
            ("post", "/coach", {"question": "What happened?"}, 422),
        )

        for method, path, payload, expected_status in cases:
            with self.subTest(path=path, payload=payload):
                response = getattr(self.client, method)(path, json=payload)

                self.assertEqual(expected_status, response.status_code)

    def test_error_mapping_for_analysis_errors(self) -> None:
        cases: tuple[tuple[Exception, int, str], ...] = (
            (ValueError("bad pgn"), 400, "Invalid PGN or analysis input: bad pgn"),
            (StockfishUnavailableError("missing"), 503, "Stockfish unavailable: missing"),
            (RuntimeError("boom"), 500, "Unexpected API error."),
        )

        for exc, expected_status, expected_detail in cases:
            with self.subTest(exc=type(exc).__name__):
                with patch.object(api_module, "analyze_pgn", side_effect=exc):
                    response = self.client.post("/analyze", json={"pgn": "1. e4 *"})

                self.assertEqual(expected_status, response.status_code)
                self.assertEqual(expected_detail, response.json()["detail"])

    def test_error_mapping_for_provider_errors(self) -> None:
        cases: tuple[tuple[Exception, int, str], ...] = (
            (OllamaUnavailableError("serve missing"), 503, "Ollama unavailable: serve missing"),
            (
                OllamaModelNotFoundError("pull model"),
                503,
                "Ollama model not found: pull model",
            ),
            (EmptyLLMResponseError("blank"), 502, "Empty LLM response: blank"),
            (OllamaProviderError("local failure"), 502, "LLM provider error: local failure"),
            (LLMProviderError("provider failure"), 502, "LLM provider error: provider failure"),
        )

        for exc, expected_status, expected_detail in cases:
            with self.subTest(exc=type(exc).__name__):
                with (
                    patch.object(api_module, "analyze_pgn", return_value=populated_result()),
                    patch.object(
                        api_module,
                        "build_ollama_client",
                        return_value=RaisingLLMClient(exc),
                    ),
                ):
                    response = self.client.post(
                        "/coach",
                        json={"pgn": "1. e4 *", "question": "What happened?"},
                    )

                self.assertEqual(expected_status, response.status_code)
                self.assertEqual(expected_detail, response.json()["detail"])

    def test_cors_allows_local_vite_origin(self) -> None:
        response = self.client.options(
            "/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "http://localhost:5173",
            response.headers["access-control-allow-origin"],
        )

    def test_analyze_pgn_closes_engine(self) -> None:
        fake_engine = FakeEngine()
        fake_pipeline = FakePipeline(populated_result())

        with (
            patch.object(api_module, "StockfishEngine", return_value=fake_engine),
            patch.object(
                api_module,
                "build_default_game_analysis_pipeline",
                return_value=fake_pipeline,
            ) as pipeline_builder,
        ):
            result = api_module.analyze_pgn("1. e4 *")

        self.assertIs(result, fake_pipeline.result)
        self.assertEqual(["1. e4 *"], fake_pipeline.pgn_texts)
        pipeline_builder.assert_called_once_with(fake_engine)
        self.assertTrue(fake_engine.closed)

    def test_build_ollama_client_constructs_ollama_only_client(self) -> None:
        with patch.object(api_module, "OllamaLLMClient") as client_class:
            client = api_module.build_ollama_client(
                model="llama3.2:3b",
                base_url="http://localhost:11434",
            )

        self.assertIs(client, client_class.return_value)
        client_class.assert_called_once_with(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )

    def test_api_source_respects_architecture_boundaries(self) -> None:
        source = Path("src/ai_chess_coach/api/app.py").read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("openai", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("board.attackers", lower_source)
        self.assertNotIn("def detect", lower_source)
        self.assertNotIn("pgn_text,", lower_source)
        self.assertIn("LLMChatCoach", source)
        self.assertIn("OllamaLLMClient", source)


class FakeEngine:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakePipeline:
    def __init__(self, result: GameAnalysisResult) -> None:
        self.result = result
        self.pgn_texts: list[str] = []

    def analyze_pgn(self, pgn_text: str) -> GameAnalysisResult:
        self.pgn_texts.append(pgn_text)
        return self.result


def populated_result() -> GameAnalysisResult:
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    before_position = board.copy(stack=False)
    san = board.san(move)
    board.push(move)
    after_position = board.copy(stack=False)
    transition = MoveTransition(
        ply=1,
        san=san,
        move=move,
        before_position=before_position,
        after_position=after_position,
    )
    event = DetectedEvent(
        event_type="hanging_piece_created",
        side=chess.WHITE,
        move=move,
        position=after_position,
        squares=(chess.E4,),
        metadata=EventMetadata(
            before_fen=before_position.fen(),
            after_fen=after_position.fen(),
            move_uci=move.uci(),
            move_san=san,
            ply=transition.ply,
        ),
        evidence={
            "piece_square": "e4",
            "piece": "P",
            "piece_color": "white",
            "attackers": ("d5",),
            "defenders": (),
        },
        severity=1.5,
    )
    verified_event = VerifiedEvent(
        event=event,
        engine_assessment=EngineAssessment(
            eval_before=10,
            eval_after=-40,
            eval_delta=-50,
            best_move=move,
            principal_variation=(move,),
            depth=12,
            eval_delta_for_event_side=-50,
            impact_magnitude=50,
            event_impact_for_side=-50,
            score_before=EngineScore(centipawns=10),
            score_after=EngineScore(centipawns=-40),
            event_score_kind="centipawn",
            event_impact_rank_for_side=-50,
            impact_rank=50,
        ),
    )
    pattern = DetectedPattern(
        pattern_type="hanging_piece_created",
        frequency=1,
        severity=50.0,
        supporting_events=(verified_event,),
    )
    profile = WeaknessProfile(
        strengths=(),
        weaknesses=(pattern,),
        recurring_themes=(pattern,),
        execution_strengths=(),
    )
    moment = CoachingMoment(
        title="Move 1: Piece safety issue",
        explanation="A selected coaching moment was found.",
        supporting_evidence=(verified_event,),
        position_reference=after_position.fen(),
        highlights=(chess.E4,),
    )

    return GameAnalysisResult(
        transitions=(transition,),
        detected_events=(event,),
        verified_events=(verified_event,),
        detected_patterns=(pattern,),
        weakness_profile=profile,
        coaching_moments=(moment,),
    )
