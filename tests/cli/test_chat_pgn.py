"""Tests for the Ollama-backed PGN chat CLI."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

import chess

from ai_chess_coach.cli import chat_pgn
from ai_chess_coach.coaching import LLMPrompt
from ai_chess_coach.coaching.providers import (
    EmptyLLMResponseError,
    LLMProviderError,
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


class FakeEngine:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakePipeline:
    def __init__(self, result: GameAnalysisResult | None = None) -> None:
        self.result = result or empty_result()
        self.pgn_texts: list[str] = []

    def analyze_pgn(self, pgn_text: str) -> GameAnalysisResult:
        self.pgn_texts.append(pgn_text)
        return self.result


class RaisingPipeline:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def analyze_pgn(self, pgn_text: str) -> GameAnalysisResult:
        raise self.exc


class RecordingLLMClient:
    def __init__(self, response: str = "grounded local answer") -> None:
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


class ChatPgnCliTest(unittest.TestCase):
    def test_format_answer_includes_summary_and_answer(self) -> None:
        output = chat_pgn.format_answer("Study forks.", populated_result())

        self.assertIn("AI Chess Coach Answer", output)
        self.assertIn("Using 1 selected coaching moments and weakness profile evidence.", output)
        self.assertIn("Study forks.", output)

    def test_main_success_uses_ollama_evidence_path_and_closes_engine(self) -> None:
        pgn_text = '[Event "Secret raw PGN marker"]\n\n1. e4 *\n'
        fake_engine = FakeEngine()
        fake_pipeline = FakePipeline(populated_result())
        fake_client = RecordingLLMClient(response="review your forks")
        built_clients: list[tuple[str | None, str | None]] = []

        def fake_build_client(*, model: str | None, base_url: str | None) -> RecordingLLMClient:
            built_clients.append((model, base_url))
            return fake_client

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write(pgn_text)
            pgn_file.flush()
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(chat_pgn, "StockfishEngine", return_value=fake_engine),
                patch.object(
                    chat_pgn,
                    "build_default_game_analysis_pipeline",
                    return_value=fake_pipeline,
                ) as pipeline_builder,
                patch.object(chat_pgn, "build_ollama_client", side_effect=fake_build_client),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = chat_pgn.main(
                    [
                        pgn_file.name,
                        "What should I improve?",
                        "--model",
                        "qwen2.5:7b",
                        "--ollama-base-url",
                        "http://localhost:11434",
                    ]
                )

        self.assertEqual(0, exit_code)
        self.assertEqual([pgn_text], fake_pipeline.pgn_texts)
        pipeline_builder.assert_called_once_with(fake_engine)
        self.assertEqual([("qwen2.5:7b", "http://localhost:11434")], built_clients)
        self.assertTrue(fake_engine.closed)
        self.assertIn("AI Chess Coach Answer", stdout.getvalue())
        self.assertIn("review your forks", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())
        assert fake_client.received_prompt is not None
        self.assertIn("What should I improve?", fake_client.received_prompt.user)
        self.assertIn("Move 1: Piece safety issue", fake_client.received_prompt.user)
        self.assertIn("Weaknesses: Hanging Piece Created", fake_client.received_prompt.user)
        self.assertNotIn("Secret raw PGN marker", fake_client.received_prompt.user)

    def test_build_ollama_client_constructs_ollama_client(self) -> None:
        with patch.object(chat_pgn, "OllamaLLMClient") as client_class:
            client = chat_pgn.build_ollama_client(
                model="llama3.2:3b",
                base_url="http://localhost:11434",
            )

        self.assertIs(client, client_class.return_value)
        client_class.assert_called_once_with(
            model="llama3.2:3b",
            base_url="http://localhost:11434",
        )

    def test_main_missing_file_returns_one(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = chat_pgn.main(["/definitely/not/a/game.pgn", "Question?"])

        self.assertEqual(1, exit_code)
        self.assertIn("PGN file not found:", stderr.getvalue())

    def test_main_stockfish_unavailable_returns_two(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write('[Event "CLI Test"]\n\n1. e4 *\n')
            pgn_file.flush()
            stderr = io.StringIO()
            with (
                patch.object(
                    chat_pgn,
                    "StockfishEngine",
                    side_effect=StockfishUnavailableError("missing"),
                ),
                redirect_stderr(stderr),
            ):
                exit_code = chat_pgn.main([pgn_file.name, "Question?"])

        self.assertEqual(2, exit_code)
        self.assertIn("Stockfish unavailable: missing", stderr.getvalue())

    def test_main_invalid_pgn_returns_three_and_closes_engine(self) -> None:
        fake_engine = FakeEngine()

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
            pgn_file.write("bad")
            pgn_file.flush()
            stderr = io.StringIO()
            with (
                patch.object(chat_pgn, "StockfishEngine", return_value=fake_engine),
                patch.object(
                    chat_pgn,
                    "build_default_game_analysis_pipeline",
                    return_value=RaisingPipeline(ValueError("bad pgn")),
                ),
                redirect_stderr(stderr),
            ):
                exit_code = chat_pgn.main([pgn_file.name, "Question?"])

        self.assertEqual(3, exit_code)
        self.assertTrue(fake_engine.closed)
        self.assertIn("Invalid PGN or analysis input: bad pgn", stderr.getvalue())

    def test_provider_errors_return_four_and_close_engine(self) -> None:
        cases: tuple[tuple[Exception, str], ...] = (
            (OllamaUnavailableError("serve is not running"), "Ollama unavailable:"),
            (OllamaModelNotFoundError("pull the model"), "Ollama model not found:"),
            (EmptyLLMResponseError("blank"), "Empty LLM response:"),
            (OllamaProviderError("local failure"), "LLM provider error:"),
            (LLMProviderError("provider failure"), "LLM provider error:"),
        )

        for exc, expected_message in cases:
            with self.subTest(exc=type(exc).__name__):
                fake_engine = FakeEngine()
                with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pgn") as pgn_file:
                    pgn_file.write('[Event "CLI Test"]\n\n1. e4 *\n')
                    pgn_file.flush()
                    stderr = io.StringIO()
                    with (
                        patch.object(chat_pgn, "StockfishEngine", return_value=fake_engine),
                        patch.object(
                            chat_pgn,
                            "build_default_game_analysis_pipeline",
                            return_value=FakePipeline(populated_result()),
                        ),
                        patch.object(
                            chat_pgn,
                            "build_ollama_client",
                            return_value=RaisingLLMClient(exc),
                        ),
                        redirect_stderr(stderr),
                    ):
                        exit_code = chat_pgn.main([pgn_file.name, "Question?"])

                self.assertEqual(4, exit_code)
                self.assertTrue(fake_engine.closed)
                self.assertIn(expected_message, stderr.getvalue())

    def test_console_script_is_declared(self) -> None:
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(
            "ai_chess_coach.cli.chat_pgn:main",
            pyproject["project"]["scripts"]["ai-chess-coach-chat"],
        )

    def test_cli_source_respects_architecture_boundaries(self) -> None:
        source = Path("src/ai_chess_coach/cli/chat_pgn.py").read_text(encoding="utf-8")
        lower_source = source.lower()

        self.assertNotIn("openai", lower_source)
        self.assertNotIn("--provider", lower_source)
        self.assertNotIn("legal_moves", lower_source)
        self.assertNotIn("attackers", lower_source)
        self.assertNotIn("def detect", lower_source)
        self.assertNotIn("promptbuilder", lower_source)


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


def empty_result() -> GameAnalysisResult:
    return GameAnalysisResult(
        transitions=(),
        detected_events=(),
        verified_events=(),
        detected_patterns=(),
        weakness_profile=WeaknessProfile(strengths=(), weaknesses=(), recurring_themes=()),
        coaching_moments=(),
    )
