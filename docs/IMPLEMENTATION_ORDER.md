# IMPLEMENTATION_ORDER.md

# Purpose

This document defines the mandatory implementation order for the AI Chess Coach project.

All contributors and coding agents must follow this order.

Do not skip phases.

Do not implement future phases before dependencies are complete.

---

# Core Rule

Build the chess intelligence engine first.

Build everything else later.

The system's primary value comes from:

- feature extraction
- detector logic
- engine verification
- weakness profiling

not from UI or infrastructure.

---

# Required Order

## Phase 1

Core Domain Models

Tasks:

- Task 1

Must be completed before any other phase.

---

## Phase 2

Replay Infrastructure

Tasks:

- Task 2

Goal:

Reliable move-by-move replay.

---

## Phase 3

Feature Infrastructure

Tasks:

- Task 3
- Task 4
- Task 5
- Task 6
- Task 7

Goal:

Reliable board understanding.

No detectors should be built before PieceSafety is complete.

---

## Phase 4

Detector Infrastructure

Tasks:

- Task 8

Goal:

Create the detector framework.

No individual detectors before this task.

---

## Phase 5

MVP Detectors

Tasks:

- Task 9
- Task 10
- Task 11

Goal:

Validate that the architecture can identify meaningful chess concepts.

These detectors form the MVP.

---

## Phase 6

Engine Verification

Tasks:

- Task 12
- Task 13
- Task 14

Goal:

Attach objective evidence to detector findings.

No profiling before verification exists.

---

## Phase 7

Pattern Aggregation

Tasks:

- Task 15
- Task 16

Goal:

Transform isolated events into recurring weaknesses.

This phase enables personalized coaching.

---

## Phase 8

Coaching Layer

Tasks:

- Task 17
- Task 18

Goal:

Generate human-facing lessons.

The coaching layer may explain evidence.

The coaching layer may not discover evidence.

---

## Phase 9

Retrieval Layer

Tasks:

- Task 19

Goal:

Support future conversational coaching.

---

## Phase 10

AI Coach

Tasks:

- Task 20

Goal:

Answer questions using retrieved evidence.

The AI coach is a teacher.

The AI coach is not a chess engine.

---

# Explicitly Forbidden Until Later

Do not build:

- React frontend
- Vite application
- User accounts
- Authentication
- Database persistence
- Cloud deployment
- Analytics dashboards
- Mobile applications

until the chess intelligence engine is validated.

---

# Definition of MVP Completion

The MVP is complete when:

1. PGNs can be replayed.
2. PieceSafety can be computed.
3. Hanging pieces can be detected.
4. Forks can be detected.
5. Knight outposts can be detected.
6. Events can be verified by Stockfish.
7. Weakness profiles can be generated.
8. Game reviews can be produced.

Only after MVP completion should frontend development begin.

---

# Future Expansion

After MVP completion, future tasks may include:

- Additional detectors
- Database storage
- Embeddings and RAG
- Puzzle recommendations
- Master game retrieval
- FastAPI backend
- React frontend
- User accounts
- Progress tracking
- Weekly coaching reports

These are intentionally out of scope for the initial implementation.
