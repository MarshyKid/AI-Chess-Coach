# ARCHITECTURE.md

# System Architecture

This document describes the backend architecture for AI Chess Coach.

The project is built around one central idea:

> Chess correctness comes from structured analysis and engine verification. The LLM only explains verified evidence.

---

# Mandatory System Flow

The required system flow is:

```text
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
```

This flow must not be bypassed.

Forbidden flow:

```text
PGN
↓
LLM
↓
Chess Analysis
```

---

# Architectural Goals

The architecture should be:

- deterministic
- testable
- modular
- backend-first
- suitable for future API and frontend layers

The first priority is the chess intelligence engine, not the user interface.

---

# Layer Overview

## 1. Replay Layer

Responsible for reconstructing games move by move.

Input:

- PGN

Output:

- `MoveTransition`

Expected package:

```text
src/ai_chess_coach/analysis/
```

Responsibilities:

- load PGN files or PGN strings
- replay legal moves
- generate before/after board states
- generate SAN notation
- create one `MoveTransition` per move

Must not:

- run detectors
- call Stockfish
- call LLMs
- generate coaching text

---

## 2. Position Analysis Layer

Responsible for representing board snapshots prepared for analysis.

Input:

- board state

Output:

- `PositionAnalysis`

Expected package:

```text
src/ai_chess_coach/models/
```

Responsibilities:

- store board state
- store FEN
- expose or reference `FeatureStore`

Must not:

- perform detector logic
- call Stockfish
- generate explanations

---

## 3. Feature Layer

Responsible for reusable chess facts.

Input:

- board or `PositionAnalysis`

Output:

- cached board features

Expected package:

```text
src/ai_chess_coach/features/
```

Examples of features:

- pinned pieces
- attack maps
- defender maps
- piece safety
- mobility
- pawn structure
- SEE values

Rules:

- `FeatureStore` is the single source of reusable chess facts.
- Detectors should consume `FeatureStore` rather than recalculating board facts.
- Features should be lazily computed and cached where practical.

Must not:

- call LLMs
- generate coaching text
- access databases
- decide long-term player weaknesses

---

## 4. Detector Layer

Responsible for identifying chess concepts from move transitions and features.

Input:

- `MoveTransition`
- `PositionAnalysis`
- `FeatureStore`

Output:

- `DetectedEvent`

Expected package:

```text
src/ai_chess_coach/detectors/
```

Initial detectors:

- `HangingPieceDetector`
- `ForkDetector`
- `KnightOutpostDetector`

Detector rules:

- every detector inherits `BaseDetector`
- every detector implements `detect()`
- every detector returns `list[DetectedEvent]`
- detectors are deterministic
- detectors are unit tested

Must not:

- call Stockfish
- call LLMs
- generate coaching text
- access databases
- duplicate FeatureStore calculations

---

## 5. Engine Verification Layer

Responsible for objective engine analysis.

Input:

- position
- move
- `DetectedEvent`

Output:

- `EngineAssessment`
- `VerifiedEvent`

Expected package:

```text
src/ai_chess_coach/engine/
```

Responsibilities:

- manage Stockfish integration
- evaluate before/after positions
- calculate evaluation delta
- retrieve best move
- retrieve principal variation when available
- attach engine evidence to detected events

Rules:

- Only this layer may communicate with Stockfish.
- Detectors must never import or call Stockfish.
- Engine verification measures importance; it does not replace detectors.

---

## 6. Profiling Layer

Responsible for aggregating verified events into recurring player tendencies.

Input:

- `VerifiedEvent`

Output:

- `DetectedPattern`
- `WeaknessProfile`

Expected package:

```text
src/ai_chess_coach/profiling/
```

Responsibilities:

- group events by type
- count recurring mistakes
- summarize frequency and severity
- build long-term weakness profiles

Rules:

- Profiles are built from events and patterns.
- Profiles are not built directly from raw PGNs.
- Profiles are not generated directly by an LLM.

---

## 7. Coaching Layer

Responsible for turning verified evidence into user-facing lessons.

Input:

- `VerifiedEvent`
- `DetectedPattern`
- `WeaknessProfile`

Output:

- `CoachingMoment`
- game review summaries

Expected package:

```text
src/ai_chess_coach/coaching/
```

Responsibilities:

- generate human-facing coaching moments
- produce game review summaries
- explain why verified events matter

Rules:

- Coaching may contain human-facing language.
- Coaching must be grounded in verified evidence.
- Coaching must not invent chess facts.
- Coaching must not perform direct chess analysis.

---

## 8. Retrieval Layer

Responsible for finding relevant evidence for future conversational coaching.

Input:

- user query or coaching need
- verified events
- detected patterns
- weakness profiles

Output:

- relevant evidence bundle

Expected package:

```text
src/ai_chess_coach/retrieval/
```

Responsibilities:

- retrieve relevant verified events
- retrieve relevant detected patterns
- retrieve relevant weakness profile data
- prepare structured context for the coach

Rules:

- Retrieval finds evidence.
- Retrieval does not create chess facts.
- Retrieval does not replace detectors.

---

## 9. LLM Coach Layer

Responsible for conversational teaching using retrieved evidence.

Input:

- retrieved evidence
- coaching moments
- weakness profile data

Output:

- natural language response

Expected package:

```text
src/ai_chess_coach/coaching/
```

Responsibilities:

- answer user questions
- explain recurring weaknesses
- summarize patterns
- recommend training themes

Rules:

- The LLM coach is not a chess engine.
- The LLM coach must not analyze raw PGNs directly.
- The LLM coach must not determine chess correctness.
- The LLM coach must use retrieved evidence.

---

# Data Ownership By Layer

| Data | Owner Layer |
|---|---|
| PGN loading | Replay Layer |
| MoveTransition | Replay Layer / Models |
| PositionAnalysis | Position Analysis Layer / Models |
| Board features | Feature Layer |
| DetectedEvent | Detector Layer / Models |
| EngineAssessment | Engine Layer / Models |
| VerifiedEvent | Engine Layer / Models |
| DetectedPattern | Profiling Layer / Models |
| WeaknessProfile | Profiling Layer / Models |
| CoachingMoment | Coaching Layer / Models |
| Retrieved evidence | Retrieval Layer |
| Natural language response | LLM Coach Layer |

---

# Backend-First Boundary

The chess intelligence backend MVP is now validated enough to support a
product-facing vertical slice. The next layers should still respect backend
ownership of chess correctness.

Do not build these unless the current task explicitly calls for them:

- authentication
- user accounts
- database persistence
- deployment infrastructure
- analytics dashboards
- mobile applications

The product-facing vertical slice may add a minimal API and Vite React frontend,
but those layers must consume backend analysis outputs.

---

# Future Frontend Boundary

The minimal frontend phase may use:

- Vite
- React
- TypeScript

The frontend should consume backend APIs.

The frontend must not:

- contain chess analysis logic
- contain detector logic
- call Stockfish directly
- analyze raw PGNs directly

Board rendering should be based on backend-provided data such as:

- FEN
- highlighted squares
- arrows
- variations
- event IDs

---

# Technical MVP Architecture

The Technical MVP is complete when the system can:

1. load and replay PGNs
2. generate `MoveTransition` objects
3. create `PositionAnalysis` objects
4. compute `FeatureStore` facts
5. compute `PieceSafety`
6. detect hanging-piece events
7. verify hanging-piece events using Stockfish
8. pass tests

---

# Coaching MVP Architecture

The Coaching MVP is complete when the system can:

1. detect forks
2. detect knight outposts
3. aggregate verified events into patterns
4. build weakness profiles
5. generate coaching moments
6. produce game review summaries
7. pass tests

---

# Product-Facing Vertical Slice

The next milestone after the backend MVP is:

```text
PGN input -> backend analysis -> selected coaching evidence -> real LLM answer -> simple UI
```

This milestone should add, in order:

1. a real provider adapter behind `LLMClient`
2. a backend LLM CLI demo
3. a minimal backend API
4. a minimal Vite React frontend
5. a board and position viewer
6. demo polish

Detector expansion is intentionally deferred until this vertical slice is
usable. The current detector set is enough for an MVP demo.

---

# Design Constraint Summary

The most important constraints are:

1. The LLM does not perform chess analysis.
2. `FeatureStore` is the source of reusable chess facts.
3. Detectors produce `DetectedEvent` only.
4. Detectors do not call Stockfish.
5. Engine verification produces `EngineAssessment` and `VerifiedEvent`.
6. Profiling is built from verified events.
7. Coaching explains evidence but does not discover evidence.
8. Frontend development consumes backend evidence and does not perform chess analysis.
9. Detector expansion waits until after the product-facing vertical slice.
