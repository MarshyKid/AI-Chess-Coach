# AGENTS.md

# AI Chess Coach

## Mission

Build a personalized chess coaching platform that identifies recurring weaknesses across a player's games and explains them through conversational coaching.

The goal is NOT to build a chess engine.

The goal is NOT to build a move recommender.

The goal is to build a system that answers:

> Why does this player repeatedly make the same mistakes?

---

# Documentation First

Before implementing any feature:

1. Read `AGENTS.md`.
2. Read all relevant files under `/docs`.
3. Read applicable ADRs under `/docs/ADRs`.
4. Follow documented architecture.
5. Do not invent alternative architectures without approval.

If documentation is unclear:

* Stop.
* Ask for clarification.
* Do not guess.

---

# Documentation Priority

When documents conflict, follow this order:

1. `AGENTS.md`
2. ADRs under `/docs/ADRs`
3. `docs/DOMAIN_MODEL.md`
4. `docs/ARCHITECTURE.md`
5. `docs/TASKS.md`
6. `docs/IMPLEMENTATION_ORDER.md`
7. Other documentation

---

# Task Execution Rule

When asked to implement from `docs/TASKS.md`:

1. Implement only the requested task.
2. Do not implement future tasks.
3. Do not create placeholder systems for future phases unless required by the current task.
4. Stop after satisfying the current task acceptance criteria.
5. Report what changed and how to test it.

Do not work ahead.

Do not add frontend, database, authentication, deployment, or LLM functionality unless the current task explicitly requires it.

---

# Core Philosophy

The LLM is NEVER responsible for chess correctness.

Chess correctness comes from:

* Feature extraction
* Detectors
* Engine verification

The LLM may:

* Explain
* Summarize
* Teach
* Coach

The LLM may NOT:

* Determine if a move is good
* Determine if a tactic exists
* Analyze raw PGNs directly
* Replace detectors
* Replace engine verification

---

# Architectural Principles

## Principle 1 — Structured Analysis Before Language Generation

Required:

PGN
→ Replay
→ MoveTransition
→ PositionAnalysis
→ FeatureStore
→ Detector
→ DetectedEvent
→ EngineAssessment
→ VerifiedEvent
→ PatternAggregation
→ WeaknessProfile
→ Retrieval
→ LLM Coach

Forbidden:

PGN
→ LLM
→ Analysis

---

## Principle 2 — Deterministic Chess Logic

All chess logic must be:

* deterministic
* testable
* reproducible

No randomness in chess analysis.

---

## Principle 3 — Single Source of Truth

Chess facts originate from `FeatureStore`.

Detectors consume `FeatureStore`.

Detectors should not independently calculate board facts that belong in `FeatureStore`.

---

## Principle 4 — Separation of Responsibilities

`FeatureStore`:

* Produces reusable chess facts.

`Detector`:

* Identifies chess concepts.

`Engine`:

* Measures objective importance.

`Retriever`:

* Finds relevant evidence.

`LLM Coach`:

* Explains evidence.

---

# Mandatory Architecture

PGN
↓
Replay
↓
MoveTransition
↓
PositionAnalysis
↓
FeatureStore
↓
Detector
↓
DetectedEvent
↓
EngineAssessment
↓
VerifiedEvent
↓
PatternAggregation
↓
WeaknessProfile
↓
Retrieval
↓
LLM Coach

This flow must not be bypassed.

---

# Detector Rules

Every detector must:

* inherit `BaseDetector`
* implement `detect()`
* return `list[DetectedEvent]`
* be deterministic
* be unit tested

Detectors may NOT:

* call LLMs
* generate coaching text
* call Stockfish directly
* access databases directly
* perform unrelated board calculations that belong in `FeatureStore`

---

# FeatureStore Rules

`FeatureStore` is the canonical source of chess facts.

Examples:

* Piece safety
* Pinned pieces
* Mobility
* Pawn structure
* SEE
* Attack maps
* Defender maps

If a detector requires a board feature:

1. Add it to `FeatureStore`.
2. Reuse it everywhere.

Do not duplicate calculations across detectors.

---

# Event Rules

`DetectedEvent` objects are machine-facing.

`DetectedEvent` must NOT contain:

* coaching language
* recommendations
* educational text

Good:

```text
hanging_piece_created
```

Bad:

```text
You should defend your bishop.
```

---

# Engine Rules

Only the engine layer may communicate with Stockfish.

Detectors may never call Stockfish.

The engine layer is responsible for:

* evaluations
* best moves
* principal variations
* significance scoring

---

# Coaching Rules

The coach explains evidence.

The coach does not discover evidence.

Inputs:

* `VerifiedEvent`
* `DetectedPattern`
* `WeaknessProfile`
* Example positions

Outputs:

* `CoachingMoment`
* Explanations
* Recommendations

The coaching layer may explain why something matters.

The coaching layer may not decide whether the chess fact is true.

---

# Backend First

Until explicitly instructed otherwise, DO NOT build:

* React applications
* Vite applications
* frontend components
* authentication
* user accounts
* deployment infrastructure
* database persistence
* dashboards
* mobile applications

Current priority:

Chess intelligence engine.

Success criteria:

Given a PGN:

* replay the game
* extract features
* detect events
* verify events
* generate weakness profiles

---

# Repository Structure

Use this package structure:

```text
src/ai_chess_coach/
  analysis/
  coaching/
  detectors/
  engine/
  features/
  models/
  profiling/
  retrieval/

tests/
  analysis/
  coaching/
  detectors/
  engine/
  features/
  models/
  profiling/
  retrieval/

docs/
  ADRs/
```

New code must follow this structure.

Do not create alternative top-level architectures.

---

# Project Commands

Use `uv` for dependency and command execution.

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run python -m unittest discover -s tests
```

Run a specific test file:

```bash
uv run python -m unittest tests.path.to_test_file
```

If formatting tools are configured, prefer:

```bash
uv run ruff format .
```

If linting tools are configured, prefer:

```bash
uv run ruff check .
```

Do not introduce new package managers unless explicitly instructed.

---

# Coding Standards

Python 3.12+

Required:

* type hints
* dataclasses where appropriate
* small focused classes
* composition over inheritance
* unit tests
* deterministic behavior
* clear names

Avoid:

* global mutable state
* god objects
* deep inheritance hierarchies
* premature optimization
* hidden side effects
* unnecessary abstractions

---

# Testing Requirements

All detectors require tests.

Tests should verify:

* positive cases
* negative cases
* edge cases

Every bug fix should include a regression test.

All core domain models should have tests for derived properties.

---

# Future Frontend

A frontend may eventually be built using:

* React
* Vite
* TypeScript

However:

* frontend must consume APIs
* frontend must not contain chess analysis logic
* frontend must not call Stockfish directly
* frontend must not perform detector logic
* all chess intelligence remains in the backend

---

# Definition of Success

The system should eventually answer:

> Why am I stuck at 1500?

using:

* recurring patterns
* verified evidence
* examples from the user's own games

rather than:

> Stockfish says -2.3.
