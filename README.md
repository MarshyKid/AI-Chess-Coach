# AI Chess Coach

AI Chess Coach is a personalized chess analysis project that looks for recurring
mistake patterns in a player's games and turns verified evidence into coaching
moments.

The key design choice is that the LLM does **not** decide chess correctness.
Chess facts come from deterministic replay, feature extraction, detectors, and
Stockfish-backed verification. The LLM is only used to explain already verified
evidence in plain language.

```text
PGN
-> replay
-> MoveTransition
-> FeatureStore
-> detectors
-> DetectedEvent
-> engine verification
-> VerifiedEvent
-> pattern aggregation
-> WeaknessProfile
-> CoachingMoment
-> grounded LLM explanation
```

## Why This Project Exists

Most chess tools answer, "What was the best move?"

This project is aimed at a different question:

> Why does this player keep making the same kind of mistake?

That framing makes the project less about engine strength and more about
software architecture: reliable domain modeling, deterministic analysis,
evidence pipelines, and careful LLM boundaries.

## Current Capabilities

- Parses and replays PGN games into move-by-move transitions.
- Computes reusable chess facts through a cached `FeatureStore`.
- Detects selected tactical and positional motifs:
  - hanging pieces
  - forks
  - knight outposts
- Verifies detected events with Stockfish through a dedicated engine layer.
- Handles candidate-aware events such as missed tactics and allowed replies.
- Preserves mate-aware engine evidence without pretending mate scores are
  centipawns.
- Aggregates verified events into detected patterns and weakness profiles.
- Selects a small number of coaching moments from noisier raw event output.
- Builds grounded prompts from structured evidence only.
- Supports:
  - backend CLI analysis
  - local Ollama-backed chat CLI
  - FastAPI local backend API
  - local Vite + React interface for PGN analysis, coaching moments,
  weakness profiles, interactive board positions, and Ollama-backed chat

## Architecture Highlights

### LLM Boundary

The LLM receives selected `CoachingMoment` and `WeaknessProfile` evidence. It
does not receive raw PGN as evidence and is explicitly instructed not to infer
material, tactics, legal moves, or board features from FEN strings.

### Detector Boundary

Detectors are deterministic and machine-facing. They emit `DetectedEvent`
objects with structured evidence, but no coaching prose. Detectors do not call
Stockfish, LLMs, databases, or frontend code.

### Engine Boundary

Only the engine layer talks to Stockfish. Engine output is converted into
structured `EngineAssessment` and `VerifiedEvent` objects before profiling or
coaching layers use it.

### Product Boundary

The frontend and API are thin product-facing layers over the backend pipeline.
They do not contain chess analysis logic.

## Tech Stack

Backend:

- Python 3.12+
- `python-chess`
- Stockfish via the `python-chess` engine API
- FastAPI for the local API
- `unittest`
- `uv`

LLM adapters:

- Ollama local provider adapter
- optional OpenAI provider adapter
- provider-agnostic `LLMClient` protocol

Frontend:

- Vite
- React
- TypeScript

## Repository Layout

```text
src/ai_chess_coach/
  analysis/      PGN loading and replay
  features/      cached board facts
  detectors/     deterministic motif detectors
  engine/        Stockfish wrapper and event verification
  profiling/     pattern aggregation and weakness profiles
  coaching/      coaching moments, prompts, LLM chat orchestration
  retrieval/     evidence retrieval helpers
  api/           FastAPI local-development API
  cli/           command-line demos
  models/        domain models

frontend/        Vite + React + TypeScript UI
tests/           unit and regression tests
docs/            architecture, roadmap, and design notes
```

## Running Locally

### 1. Install Backend Dependencies

```bash
uv sync --extra api
```

For the optional OpenAI adapter:

```bash
uv sync --extra openai
```

### 2. Install Stockfish

The real analysis pipeline needs a Stockfish executable available on `PATH`, or
configured with:

```bash
export STOCKFISH_PATH=/path/to/stockfish
```

### 3. Run Backend Tests

```bash
uv run python -m unittest discover -s tests
```

The automated tests use fakes where appropriate and do not require a real
Ollama server, OpenAI API key, or network calls.

### 4. Analyze A PGN From The CLI

```bash
uv run ai-chess-coach-analyze tests/fixtures/pgns/fork_game.pgn
```

### 5. Ask A Local LLM Question With Ollama

Install Ollama separately, then:

```bash
ollama pull llama3.2:3b
ollama serve
```

In another terminal:

```bash
uv run ai-chess-coach-chat tests/fixtures/pgns/fork_game.pgn "What should I improve?"
```

### 6. Run The Local API

```bash
uv run uvicorn ai_chess_coach.api.app:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze endpoint:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"pgn": "[Event \"Example\"]\n\n1. e4 *"}'
```

### 7. Run The Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The frontend expects the backend API at `http://127.0.0.1:8000` by default.

## Testing

Full backend suite:

```bash
uv run python -m unittest discover -s tests
```

Frontend type check/build:

```bash
cd frontend
npm run build
```

Golden PGN regression tests live in `tests/fixtures/pgns/` and exercise the real
replay and detector pipeline with deterministic fake verification.

## What I Wanted To Demonstrate

This repo is meant to show:

- layered backend architecture
- domain-driven modeling
- deterministic analysis before language generation
- testable AI boundaries
- practical use of external engines and LLM providers without coupling core
  logic to them
- product thinking around a local MVP, not just isolated scripts

## Current Limitations

- Detector coverage is intentionally small and MVP-focused.
- The frontend implements the complete local MVP flow, but it is not yet
  polished or deployed as a production application.
- No user accounts, persistence, deployment, or game history database yet.
- LLM output quality depends on the configured provider/model, especially for
  local Ollama models.

## Status

## Status

The current repository implements a working local vertical slice:

```text
paste PGN
-> deterministic backend analysis
-> Stockfish-verified coaching moments
-> interactive board positions
-> weakness profile
-> local Ollama coaching
```

Future work would include richer board interaction, more detectors, persistence,
and a more polished frontend experience.
