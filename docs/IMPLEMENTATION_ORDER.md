# IMPLEMENTATION_ORDER.md

# Purpose

This document defines the mandatory implementation order for the AI Chess Coach project.

All contributors and coding agents must follow this order.

Do not skip phases.

Do not implement future phases before dependencies are complete.

---

# Core Rule

Build the chess intelligence engine first.

The backend MVP chess intelligence engine is now complete enough for a working
demo. The next priority is the product-facing vertical slice, not expanding
detector breadth.

The system's primary value comes from:

* feature extraction
* detector logic
* engine verification
* weakness profiling

not from UI or infrastructure.

Current next milestone:

```text
PGN input -> backend analysis -> selected coaching evidence -> real LLM answer -> simple UI
```

---

# Current Allowed Scope

Unless explicitly instructed otherwise, only work on the current task from `docs/TASKS.md`.

Do not create:

* placeholder APIs
* placeholder frontend folders
* placeholder database models
* placeholder LLM wrappers
* placeholder deployment configuration
* future feature stubs

unless the current task explicitly requires them.

---

# Required Order

## Phase 1 — Core Domain Models

Tasks:

* Task 1

Goal:

Define the core data structures used by every later phase.

Must be completed before any other phase.

---

## Phase 2 — Replay Infrastructure

Tasks:

* Task 2

Goal:

Reliable move-by-move PGN replay.

This phase proves that games can be transformed into `MoveTransition` objects.

---

## Phase 3 — Feature Infrastructure

Tasks:

* Task 3
* Task 4
* Task 5
* Task 6
* Task 7

Goal:

Reliable board understanding.

No detectors should be built before `PieceSafety` is complete.

`FeatureStore` must be the single source of reusable chess facts.

---

## Phase 4 — Detector Infrastructure

Tasks:

* Task 8

Goal:

Create the detector framework.

No individual detectors before this task.

The detector contract must exist before detector implementations.

---

## Phase 5 — First MVP Detector

Tasks:

* Task 9

Goal:

Validate that the architecture can detect a concrete chess concept.

The first detector is `HangingPieceDetector` because piece safety is the most important tactical primitive for the MVP.

After this phase, the project should be able to detect basic hanging-piece events from replayed games.

---

## Phase 6 — Engine Verification

Tasks:

* Task 12
* Task 13
* Task 14

Goal:

Attach objective evidence to detector findings.

Engine verification may begin after `HangingPieceDetector` exists.

No profiling before verification exists.

Detectors must remain separate from Stockfish.

---

## Phase 7 — Additional MVP Detectors

Tasks:

* Task 10
* Task 11

Goal:

Expand detector coverage beyond hanging pieces.

MVP detectors:

* `HangingPieceDetector`
* `ForkDetector`
* `KnightOutpostDetector`

These detectors validate that the framework supports tactical and positional concepts.

---

## Phase 8 — Pattern Aggregation

Tasks:

* Task 15
* Task 16

Goal:

Transform isolated verified events into recurring weaknesses.

This phase enables personalized coaching.

Profiles must be built from events and patterns, not raw PGNs.

---

## Phase 9 — Coaching Layer

Tasks:

* Task 17
* Task 18

Goal:

Generate human-facing lessons.

The coaching layer may explain evidence.

The coaching layer may not discover evidence.

---

## Phase 10 — Retrieval Layer

Tasks:

* Task 19

Goal:

Support future conversational coaching by retrieving relevant evidence.

Retrieval should operate over:

* verified events
* detected patterns
* weakness profiles

---

## Phase 11 — AI Coach

Tasks:

* Task 20

Goal:

Answer questions using retrieved evidence.

The AI coach is a teacher.

The AI coach is not a chess engine.

The AI coach must not analyze raw PGNs directly.

---

## Phase 12 — Backend MVP Hardening And Grounded LLM Boundary

Tasks:

* Tasks 21-30

Goal:

Complete the backend vertical slice, selected coaching evidence, provider-agnostic
LLM prompt boundary, grounded chat wrapper, and golden PGN regression corpus.

Status:

Complete. See `docs/TASKS_21_31.md`.

---

## Phase 13 — Product-Facing Vertical Slice

Tasks:

* Tasks 31-36 in `docs/TASKS_31_40.md`

Goal:

Make the system usable as a small local product before adding more detectors.

Required order:

1. Real LLM provider adapter.
2. Backend LLM CLI demo.
3. Minimal backend API.
4. Minimal Vite React frontend.
5. Board and position viewer.
6. Product vertical slice polish.

Rules:

* The LLM still explains selected or retrieved evidence only.
* The frontend must consume backend API output.
* The frontend must not contain chess analysis, detector logic, or Stockfish calls.
* No database, auth, deployment, memory, streaming, or detector expansion unless a
  specific task says so.

---

## Phase 14 — Post-Vertical-Slice Detector Expansion

Tasks:

* Task 37 and later in `docs/TASKS_31_40.md`

Goal:

Resume detector expansion after the product-facing vertical slice exists.

Rules:

* Add one detector per task.
* Define event metadata before implementation.
* Detectors remain deterministic, engine-free, and LLM-free.
* Detector expansion must not break the API, frontend, or LLM grounding flow.

---

# Explicitly Forbidden Until Later

Do not build these outside their explicitly assigned tasks:

* user accounts
* authentication
* database persistence
* cloud deployment
* analytics dashboards
* mobile applications

The minimal API and Vite React frontend are allowed only in the product-facing
vertical slice tasks.

---

# Technical MVP

The Technical MVP is complete when:

1. PGNs can be replayed.
2. `MoveTransition` objects can be generated.
3. `FeatureStore` works.
4. `PieceSafety` can be computed.
5. Hanging pieces can be detected.
6. Hanging-piece events can be verified by Stockfish.
7. Tests pass.

This milestone proves that the core chess intelligence pipeline works.

---

# Coaching MVP

The Coaching MVP is complete when:

1. Forks can be detected.
2. Knight outposts can be detected.
3. Verified events can be aggregated into patterns.
4. Weakness profiles can be generated.
5. Game reviews can be produced.
6. Coaching moments can be generated from verified evidence.
7. Tests pass.

This milestone proves that the system can move from analysis to coaching.

---

# Frontend Eligibility

Frontend development may begin in Task 34 after the real LLM provider, LLM CLI
demo, and minimal backend API tasks are complete.

The future frontend should consume backend APIs.

The frontend must not contain:

* chess analysis logic
* detector logic
* Stockfish calls
* raw PGN analysis logic

All chess intelligence remains in the backend.

---

# Future Expansion

After the product-facing vertical slice is useful, future tasks may include:

* additional detectors
* database storage
* embeddings and RAG
* puzzle recommendations
* master game retrieval
* FastAPI backend
* React frontend
* user accounts
* progress tracking
* weekly coaching reports

Detector expansion should not be the immediate next task after the backend MVP.
