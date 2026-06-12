# TASKS.md

# AI Chess Coach Implementation Tasks

## Status Legend

- [ ] Not Started
- [-] In Progress
- [x] Complete

---

# Phase 1 — Core Foundations

## Task 1 — Core Domain Models

Status: [ ]

Dependencies:
None

Goal:
Implement the foundational domain models used throughout the system.

Deliverables:

- MoveTransition
- PositionAnalysis
- AttackerInfo
- DefenderInfo
- PieceSafety

Acceptance Criteria:

- Models implemented
- Type hints present
- Unit tests pass
- Models documented

---

## Task 2 — PGN Replay Engine

Status: [ ]

Dependencies:
Task 1

Goal:
Replay PGNs and generate MoveTransitions.

Deliverables:

- PGN loader
- Replay engine
- MoveTransition generation

Acceptance Criteria:

- PGNs load successfully
- Moves replay correctly
- MoveTransitions generated for every move
- Unit tests pass

---

## Task 3 — FeatureStore Framework

Status: [ ]

Dependencies:
Task 1

Goal:
Create the central chess feature service.

Deliverables:

- FeatureStore class
- Lazy evaluation
- Feature caching

Acceptance Criteria:

- Features computed lazily
- Features cached
- Repeated access does not recompute

---

# Phase 2 — Core Chess Features

## Task 4 — Pinned Piece Analysis

Status: [ ]

Dependencies:
Task 3

Goal:
Identify pinned pieces.

Deliverables:

- FeatureStore.pinned_pieces()

Acceptance Criteria:

- Correctly identifies pinned pieces
- Unit tests pass

---

## Task 5 — Attack Map Analysis

Status: [ ]

Dependencies:
Task 3

Goal:
Compute attackers for all occupied squares.

Deliverables:

- FeatureStore.attack_map()

Acceptance Criteria:

- Attacking pieces identified correctly
- Unit tests pass

---

## Task 6 — Defender Analysis

Status: [ ]

Dependencies:
Task 3

Goal:
Compute defenders for all occupied squares.

Deliverables:

- FeatureStore.defender_map()

Acceptance Criteria:

- Defending pieces identified correctly
- Unit tests pass

---

## Task 7 — Piece Safety Analysis

Status: [ ]

Dependencies:

- Task 4
- Task 5
- Task 6

Goal:
Generate PieceSafety objects.

Deliverables:

- FeatureStore.piece_safety()

Acceptance Criteria:

Produces:

- attackers
- defenders
- pinned status

Supports:

- is_hanging
- is_loose
- is_under_defended
- is_outnumbered

Unit tests pass.

---

# Phase 3 — Detector Framework

## Task 8 — Detector Framework

Status: [ ]

Dependencies:
Task 7

Goal:
Implement detector infrastructure.

Deliverables:

- BaseDetector
- Detector registry
- Detection pipeline

Acceptance Criteria:

- Detectors can be registered
- Detectors can be executed
- Tests pass

---

## Task 9 — HangingPieceDetector

Status: [ ]

Dependencies:
Task 8

Goal:
Detect hanging-piece related events.

Deliverables:

- HangingPieceDetector

Acceptance Criteria:

Detects:

- hanging_piece_created
- hanging_piece_ignored
- hanging_piece_lost

Tests pass.

---

## Task 10 — ForkDetector

Status: [ ]

Dependencies:
Task 8

Goal:
Detect forks.

Deliverables:

- ForkDetector

Acceptance Criteria:

Detects:

- fork_created
- fork_missed
- fork_allowed

Tests pass.

---

## Task 11 — KnightOutpostDetector

Status: [ ]

Dependencies:
Task 8

Goal:
Detect knight outposts.

Deliverables:

- KnightOutpostDetector

Acceptance Criteria:

Detects:

- knight_outpost_created
- knight_outpost_missed

Tests pass.

---

# Phase 4 — Engine Verification

## Task 12 — Stockfish Integration

Status: [ ]

Dependencies:
Task 11

Goal:
Integrate Stockfish.

Deliverables:

- Engine wrapper
- Position evaluation

Acceptance Criteria:

- Engine evaluates positions
- Tests pass

---

## Task 13 — EngineAssessment

Status: [ ]

Dependencies:
Task 12

Goal:
Represent engine evidence.

Deliverables:

- EngineAssessment

Acceptance Criteria:

Contains:

- eval_before
- eval_after
- eval_delta
- best_move
- principal_variation

Tests pass.

---

## Task 14 — VerifiedEvent

Status: [ ]

Dependencies:
Task 13

Goal:
Combine detector output with engine evidence.

Deliverables:

- VerifiedEvent

Acceptance Criteria:

VerifiedEvent =
DetectedEvent +
EngineAssessment

Tests pass.

---

# Phase 5 — Pattern Aggregation

## Task 15 — Pattern Aggregation

Status: [ ]

Dependencies:
Task 14

Goal:
Aggregate recurring themes.

Deliverables:

- PatternAggregator
- DetectedPattern

Acceptance Criteria:

Can identify recurring patterns across games.

Tests pass.

---

## Task 16 — Weakness Profiles

Status: [ ]

Dependencies:
Task 15

Goal:
Create long-term player profiles.

Deliverables:

- WeaknessProfile

Acceptance Criteria:

Produces:

- strengths
- weaknesses
- recurring themes

Tests pass.

---

# Phase 6 — Coaching Layer

## Task 17 — CoachingMoment

Status: [ ]

Dependencies:
Task 16

Goal:
Create user-facing lessons.

Deliverables:

- CoachingMoment

Acceptance Criteria:

Contains:

- title
- explanation
- supporting evidence

Tests pass.

---

## Task 18 — Game Review Generation

Status: [ ]

Dependencies:
Task 17

Goal:
Generate reviews from a game.

Deliverables:

- Review generator

Acceptance Criteria:

Produces actionable coaching summaries.

Tests pass.

---

# Phase 7 — Retrieval & AI Coach

## Task 19 — Retrieval Layer

Status: [ ]

Dependencies:
Task 16

Goal:
Retrieve evidence for coaching.

Deliverables:

- Event retrieval
- Pattern retrieval

Acceptance Criteria:

Can retrieve relevant evidence for a query.

Tests pass.

---

## Task 20 — Conversational Coach

Status: [ ]

Dependencies:

- Task 18
- Task 19

Goal:
Provide coaching through natural language.

Deliverables:

- Chat coach interface

Acceptance Criteria:

Uses retrieved evidence.

Does not perform direct chess analysis.

Tests pass.
