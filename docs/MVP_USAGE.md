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

## What This MVP Does Not Include

The backend MVP does not include:

- real LLM provider clients
- API keys or network LLM calls
- frontend UI
- database persistence
- authentication
- deployment configuration

Those remain future layers. The current focus is a deterministic backend path
from PGN analysis to grounded coaching evidence.
