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

1. Read AGENTS.md.
2. Read all relevant files under `/docs`.
3. Read applicable ADRs under `/docs/ADRs`.
4. Follow documented architecture.
5. Do not invent alternative architectures without approval.

If documentation is unclear:

- Stop.
- Ask for clarification.
- Do not guess.

---

# Documentation Priority

When documents conflict, follow this order:

1. AGENTS.md
2. ADRs
3. DOMAIN_MODEL.md
4. ARCHITECTURE.md
5. Other documentation

---

# Core Philosophy

The LLM is NEVER responsible for chess correctness.

Chess correctness comes from:

- Feature extraction
- Detectors
- Engine verification

The LLM may:

- Explain
- Summarize
- Teach
- Coach

The LLM may NOT:

- Determine if a move is good
- Determine if a tactic exists
- Analyze raw PGNs directly
- Replace detectors
- Replace engine verification

---

# Architectural Principles

## Principle 1

Structured analysis before language generation.

Required:

PGN
→ Features
→ Events
→ Verification
→ Patterns
→ Retrieval
→ LLM

Forbidden:

PGN
→ LLM
→ Analysis

---

## Principle 2

Deterministic chess logic.

All chess logic must be:

- deterministic
- testable
- reproducible

No randomness.

---

## Principle 3

Single source of truth.

Chess facts originate from FeatureStore.

Detectors consume FeatureStore.

Detectors should not independently calculate board facts.

---

## Principle 4

Separation of responsibilities.

FeatureStore:
Produces chess facts.

Detector:
Identifies concepts.

Engine:
Measures importance.

Retriever:
Finds evidence.

LLM:
Explains evidence.

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

- inherit BaseDetector
- implement detect()
- return DetectedEvent objects
- be deterministic
- be unit tested

Detectors may NOT:

- call LLMs
- generate coaching text
- call Stockfish directly
- access databases directly

---

# FeatureStore Rules

FeatureStore is the canonical source of chess facts.

Examples:

- Piece safety
- Pinned pieces
- Mobility
- Pawn structure
- SEE

If a detector requires a board feature:

1. Add it to FeatureStore.
2. Reuse it everywhere.

Do not duplicate calculations.

---

# Event Rules

DetectedEvents are machine-facing.

DetectedEvents must NOT contain:

- coaching language
- recommendations
- educational text

Good:

"hanging_piece_created"

Bad:

"You should defend your bishop"

---

# Engine Rules

Only the engine layer may communicate with Stockfish.

Detectors may never call Stockfish.

The engine layer is responsible for:

- evaluations
- best moves
- principal variations
- significance scoring

---

# Coaching Rules

The coach explains evidence.

The coach does not discover evidence.

Inputs:

- VerifiedEvents
- DetectedPatterns
- WeaknessProfiles
- Example Positions

Outputs:

- CoachingMoments
- Explanations
- Recommendations

---

# Backend First

Until explicitly instructed otherwise:

DO NOT build:

- React applications
- Frontend components
- Authentication
- User accounts
- Deployment infrastructure

Current priority:

Chess intelligence engine.

Success criteria:

Given a PGN:

- Replay game
- Extract features
- Detect events
- Verify events
- Generate weakness profile

---

# Coding Standards

Python 3.12+

Required:

- Type hints
- Dataclasses where appropriate
- Small focused classes
- Composition over inheritance
- Unit tests

Avoid:

- Global mutable state
- God objects
- Deep inheritance hierarchies
- Premature optimization

---

# Testing Requirements

All detectors require tests.

Tests should verify:

- positive cases
- negative cases
- edge cases

Every bug fix should include a regression test.

---

# Repository Structure

src/

analysis/
detectors/
engine/
features/
models/
profiling/
retrieval/
coaching/

tests/

New code should follow this structure.

Do not create alternative top-level architectures.

---

# Future Frontend

A frontend may eventually be built using:

- React
- Vite
- TypeScript

However:

Frontend must consume APIs.

Frontend must not contain chess analysis logic.

All chess intelligence remains in the backend.

---

# Definition of Success

The system should eventually answer:

"Why am I stuck at 1500?"

using:

- recurring patterns
- verified evidence
- examples from the user's own games

rather than:

"Stockfish says -2.3"
