# TASKS.md

# AI Chess Coach Implementation Tasks

## Status Legend

* [ ] Not Started
* [-] In Progress
* [x] Complete

---

# Task Execution Rule

Each task must be implemented one at a time.

When implementing a task:

1. Read `AGENTS.md`.
2. Read relevant docs under `/docs`.
3. Implement only the requested task.
4. Do not implement future tasks.
5. Add or update tests.
6. Run tests.
7. Stop after acceptance criteria are satisfied.

---

# Phase 1 — Core Foundations

## Task 1 — Core Domain Models

Status: [ ]

Dependencies:

None

Goal:

Implement the foundational domain models used throughout the system.

Files to create or update:

```text
src/ai_chess_coach/models/__init__.py
src/ai_chess_coach/models/move_transition.py
src/ai_chess_coach/models/position_analysis.py
src/ai_chess_coach/models/piece_safety.py
tests/models/test_piece_safety.py
tests/models/test_move_transition.py
```

Deliverables:

* `MoveTransition`
* `PositionAnalysis`
* `AttackerInfo`
* `DefenderInfo`
* `PieceSafety`

Required model expectations:

`MoveTransition` should represent one move and include:

* ply
* SAN
* move
* before position
* after position

`PositionAnalysis` should represent one board snapshot and include:

* board
* FEN
* feature store reference, if available

`AttackerInfo` should include:

* square
* piece
* is_pinned

`DefenderInfo` should include:

* square
* piece
* is_pinned
* is_overloaded

`PieceSafety` should include:

* square
* piece
* attackers
* defenders
* is_pinned
* SEE value, if available

Derived properties:

* `is_hanging`
* `is_loose`
* `is_under_defended`
* `is_outnumbered`

Acceptance Criteria:

* Models implemented
* Type hints present
* Dataclasses used where appropriate
* Derived properties tested
* Unit tests pass

---

## Task 2 — PGN Replay Engine

Status: [ ]

Dependencies:

* Task 1

Goal:

Replay PGNs and generate `MoveTransition` objects.

Files to create or update:

```text
src/ai_chess_coach/analysis/__init__.py
src/ai_chess_coach/analysis/pgn_loader.py
src/ai_chess_coach/analysis/replay.py
tests/analysis/test_pgn_loader.py
tests/analysis/test_replay.py
```

Deliverables:

* PGN loader
* Replay engine
* MoveTransition generation

Acceptance Criteria:

* PGNs load successfully
* Legal moves replay correctly
* One `MoveTransition` generated for every move
* Before and after positions are correct
* SAN is captured correctly
* Unit tests pass

---

## Task 3 — FeatureStore Framework

Status: [ ]

Dependencies:

* Task 1

Goal:

Create the central chess feature service.

Files to create or update:

```text
src/ai_chess_coach/features/__init__.py
src/ai_chess_coach/features/feature_store.py
tests/features/test_feature_store.py
```

Deliverables:

* `FeatureStore` class
* Lazy evaluation
* Feature caching

Acceptance Criteria:

* FeatureStore accepts a board or position snapshot
* Features are computed lazily
* Features are cached
* Repeated access does not recompute the same feature
* Unit tests pass

---

# Phase 2 — Core Chess Features

## Task 4 — Pinned Piece Analysis

Status: [ ]

Dependencies:

* Task 3

Goal:

Identify pinned pieces.

Files to create or update:

```text
src/ai_chess_coach/features/feature_store.py
tests/features/test_pinned_pieces.py
```

Deliverables:

* `FeatureStore.pinned_pieces()`

Acceptance Criteria:

* Correctly identifies pinned pieces
* Handles positions with no pins
* Handles absolute pins to the king
* Unit tests pass

---

## Task 5 — Attack Map Analysis

Status: [ ]

Dependencies:

* Task 3

Goal:

Compute attackers for occupied squares.

Files to create or update:

```text
src/ai_chess_coach/features/feature_store.py
tests/features/test_attack_map.py
```

Deliverables:

* `FeatureStore.attack_map()`

Acceptance Criteria:

* Attacking pieces identified correctly
* Empty squares are not included unless explicitly needed
* Occupied squares are mapped to attackers
* Unit tests pass

---

## Task 6 — Defender Analysis

Status: [ ]

Dependencies:

* Task 3

Goal:

Compute defenders for occupied squares.

Files to create or update:

```text
src/ai_chess_coach/features/feature_store.py
tests/features/test_defender_map.py
```

Deliverables:

* `FeatureStore.defender_map()`

Acceptance Criteria:

* Defending pieces identified correctly
* Own pieces defending a square are handled correctly
* Empty squares are not included unless explicitly needed
* Unit tests pass

---

## Task 7 — Piece Safety Analysis

Status: [ ]

Dependencies:

* Task 4
* Task 5
* Task 6

Goal:

Generate `PieceSafety` objects for occupied squares.

Files to create or update:

```text
src/ai_chess_coach/features/feature_store.py
src/ai_chess_coach/models/piece_safety.py
tests/features/test_piece_safety_feature.py
```

Deliverables:

* `FeatureStore.piece_safety()`

Acceptance Criteria:

Produces:

* attackers
* defenders
* pinned status

Supports:

* `is_hanging`
* `is_loose`
* `is_under_defended`
* `is_outnumbered`

Rules:

* Empty squares should not appear in the piece safety map.
* Piece safety is about pieces, not squares.
* Unit tests pass.

---

# Phase 3 — Detector Framework

## Task 8 — Detector Framework

Status: [ ]

Dependencies:

* Task 7

Goal:

Implement detector infrastructure.

Files to create or update:

```text
src/ai_chess_coach/detectors/__init__.py
src/ai_chess_coach/detectors/base.py
src/ai_chess_coach/detectors/registry.py
src/ai_chess_coach/detectors/pipeline.py
src/ai_chess_coach/models/detected_event.py
tests/detectors/test_detector_framework.py
```

Deliverables:

* `BaseDetector`
* detector registry
* detection pipeline
* `DetectedEvent`

Acceptance Criteria:

* Detectors can be registered
* Detectors can be executed
* Pipeline returns `list[DetectedEvent]`
* `DetectedEvent` contains no coaching language
* Tests pass

---

## Task 9 — HangingPieceDetector

Status: [ ]

Dependencies:

* Task 8

Goal:

Detect hanging-piece related events.

Files to create or update:

```text
src/ai_chess_coach/detectors/hanging_piece_detector.py
tests/detectors/test_hanging_piece_detector.py
```

Deliverables:

* `HangingPieceDetector`

Acceptance Criteria:

Detects:

* `hanging_piece_created`
* `hanging_piece_ignored`
* `hanging_piece_lost`

Rules:

* Use `FeatureStore`.
* Do not call Stockfish.
* Do not generate coaching text.
* Tests pass.

---

## Task 10 — ForkDetector

Status: [ ]

Dependencies:

* Task 8

Goal:

Detect forks.

Files to create or update:

```text
src/ai_chess_coach/detectors/fork_detector.py
tests/detectors/test_fork_detector.py
```

Deliverables:

* `ForkDetector`

Acceptance Criteria:

Detects:

* `fork_created`
* `fork_missed`
* `fork_allowed`

Rules:

* Use `FeatureStore`.
* Do not call Stockfish.
* Do not generate coaching text.
* Tests pass.

---

## Task 11 — KnightOutpostDetector

Status: [ ]

Dependencies:

* Task 8

Goal:

Detect knight outposts.

Files to create or update:

```text
src/ai_chess_coach/detectors/knight_outpost_detector.py
tests/detectors/test_knight_outpost_detector.py
```

Deliverables:

* `KnightOutpostDetector`

Acceptance Criteria:

Detects:

* `knight_outpost_created`
* `knight_outpost_missed`

Rules:

* Use `FeatureStore`.
* Do not call Stockfish.
* Do not generate coaching text.
* Tests pass.

---

# Phase 4 — Engine Verification

## Task 12 — Stockfish Integration

Status: [ ]

Dependencies:

* Task 9

Goal:

Integrate Stockfish through a dedicated engine wrapper.

Files to create or update:

```text
src/ai_chess_coach/engine/__init__.py
src/ai_chess_coach/engine/stockfish_engine.py
tests/engine/test_stockfish_engine.py
```

Deliverables:

* Engine wrapper
* Position evaluation

Acceptance Criteria:

* Engine wrapper can evaluate a FEN
* Engine wrapper can return best move
* Engine wrapper can return principal variation, if available
* Tests pass or are safely skipped when Stockfish is unavailable

Rules:

* Only engine layer may call Stockfish.
* Detectors must not import this module.

---

## Task 13 — EngineAssessment

Status: [ ]

Dependencies:

* Task 12

Goal:

Represent engine evidence.

Files to create or update:

```text
src/ai_chess_coach/models/engine_assessment.py
tests/models/test_engine_assessment.py
```

Deliverables:

* `EngineAssessment`

Acceptance Criteria:

Contains:

* eval_before
* eval_after
* eval_delta
* best_move
* principal_variation
* depth

Tests pass.

---

## Task 14 — VerifiedEvent

Status: [ ]

Dependencies:

* Task 13

Goal:

Combine detector output with engine evidence.

Files to create or update:

```text
src/ai_chess_coach/models/verified_event.py
src/ai_chess_coach/engine/verifier.py
tests/engine/test_verifier.py
tests/models/test_verified_event.py
```

Deliverables:

* `VerifiedEvent`
* event verifier

Acceptance Criteria:

`VerifiedEvent` combines:

* `DetectedEvent`
* `EngineAssessment`

Rules:

* Verification is separate from detection.
* Detectors must remain engine-free.
* Tests pass.

---

# Phase 5 — Pattern Aggregation

## Task 15 — Pattern Aggregation

Status: [ ]

Dependencies:

* Task 14

Goal:

Aggregate recurring themes across games.

Files to create or update:

```text
src/ai_chess_coach/profiling/__init__.py
src/ai_chess_coach/profiling/pattern_aggregator.py
src/ai_chess_coach/models/detected_pattern.py
tests/profiling/test_pattern_aggregator.py
```

Deliverables:

* `PatternAggregator`
* `DetectedPattern`

Acceptance Criteria:

* Can group events by type
* Can count recurring event types
* Can summarize severity/frequency
* Tests pass

---

## Task 16 — Weakness Profiles

Status: [ ]

Dependencies:

* Task 15

Goal:

Create long-term player profiles.

Files to create or update:

```text
src/ai_chess_coach/profiling/weakness_profile_builder.py
src/ai_chess_coach/models/weakness_profile.py
tests/profiling/test_weakness_profile_builder.py
```

Deliverables:

* `WeaknessProfile`
* weakness profile builder

Acceptance Criteria:

Produces:

* strengths
* weaknesses
* recurring themes

Rules:

* Profiles must be built from verified events and patterns.
* Profiles must not be built directly from raw PGNs.
* Tests pass.

---

# Phase 6 — Coaching Layer

## Task 17 — CoachingMoment

Status: [ ]

Dependencies:

* Task 16

Goal:

Create user-facing lesson objects.

Files to create or update:

```text
src/ai_chess_coach/models/coaching_moment.py
tests/models/test_coaching_moment.py
```

Deliverables:

* `CoachingMoment`

Acceptance Criteria:

Contains:

* title
* explanation
* supporting evidence
* position reference
* highlights, if available

Rules:

* CoachingMoment may contain human-facing language.
* DetectedEvent must not contain human-facing language.
* Tests pass.

---

## Task 18 — Game Review Generation

Status: [ ]

Dependencies:

* Task 17

Goal:

Generate reviews from a game.

Files to create or update:

```text
src/ai_chess_coach/coaching/__init__.py
src/ai_chess_coach/coaching/review_generator.py
tests/coaching/test_review_generator.py
```

Deliverables:

* review generator

Acceptance Criteria:

* Produces actionable coaching summaries
* Uses `VerifiedEvent` and `CoachingMoment`
* Does not perform direct chess analysis
* Tests pass

---

# Phase 7 — Retrieval & AI Coach

## Task 19 — Retrieval Layer

Status: [ ]

Dependencies:

* Task 14
* Task 16

Goal:

Retrieve evidence for coaching.

Files to create or update:

```text
src/ai_chess_coach/retrieval/__init__.py
src/ai_chess_coach/retrieval/evidence_retriever.py
tests/retrieval/test_evidence_retriever.py
```

Deliverables:

* event retrieval
* pattern retrieval

Acceptance Criteria:

* Can retrieve relevant verified events
* Can retrieve relevant detected patterns
* Can retrieve relevant weakness profile data
* Tests pass

---

## Task 20 — Conversational Coach

Status: [ ]

Dependencies:

* Task 18
* Task 19

Goal:

Provide coaching through natural language.

Files to create or update:

```text
src/ai_chess_coach/coaching/chat_coach.py
tests/coaching/test_chat_coach.py
```

Deliverables:

* chat coach interface

Acceptance Criteria:

* Uses retrieved evidence
* Does not perform direct chess analysis
* Does not analyze raw PGNs directly
* Does not replace detectors
* Tests pass
