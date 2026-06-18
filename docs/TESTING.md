# Testing

This project uses `uv` and Python `unittest`.

## Standard Commands

Install or sync dependencies:

```bash
uv sync
```

Run the full test suite:

```bash
uv run python -m unittest discover -s tests
```

Run a specific test module:

```bash
uv run python -m unittest tests.pipeline.test_golden_pgns
```

## Golden PGN Regression Tests

The golden PGN corpus lives in:

```text
tests/fixtures/pgns/
```

The current fixtures cover the backend MVP motifs:

- `hanging_piece_game.pgn`
- `fork_game.pgn`
- `outpost_game.pgn`

`tests/pipeline/test_golden_pgns.py` runs those fixtures through real PGN replay,
the real detector pipeline, raw pattern aggregation, weakness profile building,
review generation, and grounded prompt construction.

The golden tests intentionally use a deterministic fake verifier instead of
Stockfish. This keeps the regression corpus fast, stable, and runnable on
machines without a Stockfish binary. The fake verifier only attaches structured
engine evidence to detector output; it does not replace detector logic.

Golden assertions should stay structural:

- expected event families or event types are present
- typed candidate moves are present for candidate-aware events
- raw `VerifiedEvent` and raw `DetectedPattern` outputs are preserved
- selected `CoachingMoment` objects are backed by verified evidence
- low-impact execution strengths can appear in `WeaknessProfile.execution_strengths`
- grounded LLM prompts use supplied structured evidence

Avoid full-output snapshots and exact global event counts. Those make the tests
fragile when detector internals legitimately produce more supporting evidence.

## Optional Stockfish Tests

Unit tests do not require a bundled Stockfish binary. Tests that need a real
engine should skip safely unless either `STOCKFISH_PATH` is set or `stockfish`
is available on the system `PATH`.

The CLI demo does require Stockfish at runtime because it uses the real
`EventVerifier`.

## Adding A Golden Fixture

When adding a fixture:

1. Keep it short and legal.
2. Prefer `SetUp`/`FEN` headers when isolating a motif.
3. Use real detectors in the golden test.
4. Use deterministic fake verification unless the test is explicitly about the
   engine layer.
5. Assert stable structural properties, not full prose or full pipeline dumps.

Do not change detector semantics to make a fixture pass. Adjust the fixture or
the fixture-specific expectation instead.
