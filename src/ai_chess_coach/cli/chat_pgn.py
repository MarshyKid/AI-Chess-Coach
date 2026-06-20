"""Ask a grounded coaching question about a PGN using local Ollama."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ai_chess_coach.cli.analyze_pgn import build_default_game_analysis_pipeline
from ai_chess_coach.coaching import LLMChatCoach, LLMClient
from ai_chess_coach.coaching.providers import (
    EmptyLLMResponseError,
    LLMProviderError,
    OllamaLLMClient,
    OllamaModelNotFoundError,
    OllamaProviderError,
    OllamaUnavailableError,
)
from ai_chess_coach.engine import StockfishEngine, StockfishUnavailableError
from ai_chess_coach.models import GameAnalysisResult


def build_ollama_client(
    *,
    model: str | None,
    base_url: str | None,
) -> LLMClient:
    """Build the local Ollama LLM client for the chat demo."""

    return OllamaLLMClient(model=model, base_url=base_url)


def format_answer(answer: str, result: GameAnalysisResult) -> str:
    """Format a grounded LLM answer for deterministic CLI output."""

    return "\n".join(
        [
            "AI Chess Coach Answer",
            "",
            (
                f"Using {len(result.coaching_moments)} selected coaching moments "
                "and weakness profile evidence."
            ),
            "",
            answer,
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """Run the local Ollama-backed PGN chat demo CLI."""

    parser = argparse.ArgumentParser(
        prog="ai-chess-coach-chat",
        description="Ask a grounded coaching question about one PGN using Ollama.",
    )
    parser.add_argument("pgn_file", help="Path to a PGN file.")
    parser.add_argument("question", help="Question to ask about the analyzed game.")
    parser.add_argument("--model", help="Ollama model override.")
    parser.add_argument("--ollama-base-url", help="Ollama base URL override.")
    args = parser.parse_args(argv)

    pgn_path = Path(args.pgn_file)
    if not pgn_path.is_file():
        print(f"PGN file not found: {pgn_path}", file=sys.stderr)
        return 1

    try:
        pgn_text = pgn_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Could not read PGN file: {exc}", file=sys.stderr)
        return 1

    engine: StockfishEngine | None = None
    try:
        engine = StockfishEngine()
        pipeline = build_default_game_analysis_pipeline(engine)
        result = pipeline.analyze_pgn(pgn_text)
        llm_client = build_ollama_client(
            model=args.model,
            base_url=args.ollama_base_url,
        )
        answer = LLMChatCoach(client=llm_client).respond(
            args.question,
            coaching_moments=result.coaching_moments,
            weakness_profile=result.weakness_profile,
        )
    except StockfishUnavailableError as exc:
        print(f"Stockfish unavailable: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Invalid PGN or analysis input: {exc}", file=sys.stderr)
        return 3
    except OllamaUnavailableError as exc:
        print(f"Ollama unavailable: {exc}", file=sys.stderr)
        return 4
    except OllamaModelNotFoundError as exc:
        print(f"Ollama model not found: {exc}", file=sys.stderr)
        return 4
    except EmptyLLMResponseError as exc:
        print(f"Empty LLM response: {exc}", file=sys.stderr)
        return 4
    except (OllamaProviderError, LLMProviderError) as exc:
        print(f"LLM provider error: {exc}", file=sys.stderr)
        return 4
    finally:
        if engine is not None:
            engine.close()

    print(format_answer(answer, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
