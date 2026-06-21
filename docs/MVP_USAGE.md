# Backend MVP Usage

The backend MVP can analyze one PGN through the structured pipeline:

```text
PGN
-> replay
-> MoveTransition
-> detectors
-> DetectedEvent
-> EventVerifier
-> VerifiedEvent
-> PatternAggregator
-> WeaknessProfile
-> ReviewGenerator
-> CoachingMoment
```

The LLM layer, when used by tests or future callers, explains selected or
retrieved evidence. It does not analyze raw PGNs and does not determine chess
correctness.

## Run The CLI Demo

Analyze a PGN file with the installed console script:

```bash
uv run ai-chess-coach-analyze path/to/game.pgn
```

Equivalent module form:

```bash
uv run python -m ai_chess_coach.cli.analyze_pgn path/to/game.pgn
```

The CLI reads one PGN file, builds the default detector pipeline, verifies
events with Stockfish through the engine layer, and prints deterministic
plain-text output.

## Stockfish Requirement

The CLI requires a Stockfish executable. It can be provided by:

1. passing through normal system discovery with `stockfish` on `PATH`
2. setting `STOCKFISH_PATH` to the executable path

If Stockfish is unavailable, the CLI exits clearly with:

```text
Stockfish unavailable: ...
```

## Output Sections

The CLI prints:

- `Detected Events`: raw machine-facing detector output
- `Verified Events`: detector events with engine evidence attached
- `Detected Patterns`: raw/debug aggregation from all verified events
- `Weakness Profile`: user-facing profile-local strengths, execution strengths,
  weaknesses, and recurring themes
- `Coaching Moments`: selected user-facing teaching points with summaries and
  supporting details

Raw verified events are intentionally preserved even when only a smaller set of
coaching moments is selected for review.

## Ask A Local LLM Question With Ollama

After installing Ollama, pulling a model, and ensuring Stockfish is available,
ask a grounded coaching question with:

```bash
uv run ai-chess-coach-chat path/to/game.pgn "What should I improve?"
```

Use a different local model:

```bash
uv run ai-chess-coach-chat path/to/game.pgn "What should I improve?" --model qwen2.5:7b
```

Use a different Ollama server URL:

```bash
uv run ai-chess-coach-chat path/to/game.pgn "What should I improve?" --ollama-base-url http://localhost:11434
```

The chat CLI uses the PGN only to run the deterministic backend analysis
pipeline. It sends selected `CoachingMoment` objects and the `WeaknessProfile`
to `LLMChatCoach`; it does not send raw PGN text to the LLM.

Common runtime errors:

- `Stockfish unavailable`: configure `STOCKFISH_PATH` or put `stockfish` on `PATH`
- `Ollama unavailable`: run `ollama serve`
- `Ollama model not found`: run `ollama pull llama3.2:3b` or pass `--model`
- `Empty LLM response`: the local model returned no usable text

## Current MVP Boundary

The current MVP is backend-only. It proves the deterministic analysis and
evidence-grounded coaching path, but it is not yet a user-facing app.

The next phase is the product-facing vertical slice:

```text
PGN input -> backend analysis -> selected coaching evidence -> real LLM answer -> simple UI
```

Planned next layers:

1. backend LLM CLI demo
2. minimal backend API
3. minimal Vite React frontend
4. board and position viewer
5. demo polish

Detector expansion is intentionally postponed until after this vertical slice.

## OpenAI Provider Adapter

The backend now includes an optional OpenAI adapter behind the existing
`LLMClient` protocol:

```python
from ai_chess_coach.coaching.providers import OpenAILLMClient
```

Install the optional dependency and configure credentials only when you want to
call the real provider:

```bash
uv sync --extra openai
export OPENAI_API_KEY=...
export AI_CHESS_COACH_OPENAI_MODEL=gpt-5.4-mini
```

`AI_CHESS_COACH_OPENAI_MODEL` is optional. If omitted, the adapter uses its
documented `DEFAULT_OPENAI_MODEL`, which is intentionally easy to change as
provider model availability evolves.

The adapter is not wired into the CLI yet. The current chat CLI intentionally
uses Ollama only.

## Ollama Local Provider Adapter

The backend also includes an Ollama adapter behind `LLMClient` for no-payment
local model use:

```python
from ai_chess_coach.coaching.providers import OllamaLLMClient
```

Install and run Ollama separately, then pull a local model:

```bash
ollama pull llama3.2:3b
ollama serve
```

Optional configuration:

```bash
export AI_CHESS_COACH_OLLAMA_MODEL=llama3.2:3b
export AI_CHESS_COACH_OLLAMA_BASE_URL=http://localhost:11434
```

`llama3.2:3b` is a pragmatic small local default. If your machine can run a
larger model, alternatives such as `qwen2.5:7b` may produce better coaching
language.

Manual smoke test:

```bash
uv run python - <<'PY'
from ai_chess_coach.coaching import LLMPrompt
from ai_chess_coach.coaching.providers import OllamaLLMClient

client = OllamaLLMClient()
prompt = LLMPrompt(
    system="You are a concise test assistant. Reply in one sentence.",
    user="Say that the local Ollama provider adapter is working.",
)

print(client.generate(prompt))
PY
```

This smoke test is intentionally manual. Automated tests use fake transports and
do not require Ollama, a local server, or downloaded models.

The Ollama adapter is wired into the chat CLI. OpenAI remains an optional
provider adapter, but this CLI intentionally uses Ollama only.

Local model quality varies. The prompt explicitly tells the model that FENs and
position references are identifiers only and that selected coaching moments are
real evidence. If a small local model describes material or board features from
a FEN anyway, treat that as a model-following limitation rather than a backend
analysis result.

## What This MVP Does Not Include

The backend MVP does not include:

- API/frontend wiring for real LLM provider calls
- frontend UI
- database persistence
- authentication
- deployment configuration

Those remain future layers. The current focus is a deterministic backend path
from PGN analysis to grounded coaching evidence, followed next by a thin
product-facing loop over that evidence.
