# Development Roadmap

## Phase 1 — Core Models

Foundational domain objects used throughout the system.

- MoveTransition
- PositionAnalysis
- PieceSafety
- AttackerInfo
- DefenderInfo

## Phase 2 — Core Chess Features

Reusable board facts exposed through FeatureStore.

- attackers
- defenders
- pinned pieces
- piece safety
- SEE, if added later

## Phase 3 — Detectors

Machine-facing chess event detectors. Detectors identify what happened; they do not generate coaching language and do not call Stockfish.

- HangingPieceDetector
- ForkDetector
- KnightOutpostDetector

## Phase 4 — Engine Verification

Engine layer validates the importance of detector findings.

- Stockfish integration
- EngineAssessment
- VerifiedEvent

## Phase 5 — Pattern Aggregation And Weakness Profiling

Turn verified events into recurring themes and structured player profiles.

- Pattern aggregation
- Weakness profiles

## Phase 6 — Coaching Objects And Review Generation

Create user-facing lesson objects and deterministic reviews from verified evidence.

- CoachingMoment
- Review generation

## Phase 7 — Retrieval And Deterministic Chat

Retrieve relevant evidence and provide a deterministic chat interface over existing coaching moments.

- Evidence retrieval
- ChatCoach

## Phase 8 — Backend Vertical Slice MVP

Tie the completed pieces together into a usable backend MVP before expanding breadth.

- End-to-End Game Analysis Pipeline
- CLI demo for PGN file analysis
- Event metadata refactor

## Phase 9 — Evidence Selection And LLM-Grounded Conversation

Make the coaching output selective before introducing the key product experience: a player can have a conversation with an AI coach. The LLM is allowed to explain and synthesize retrieved/selected evidence, but it must not replace detectors, Stockfish verification, or direct chess analysis.

- Event type metadata and polarity registry
- Side-aware engine impact
- Coaching moment selection
- LLM client abstraction
- Prompt builder over retrieved/selected evidence
- LLM-grounded coach
- Grounding and safety tests

## Phase 10 — Backend MVP Hardening

Harden the backend MVP after the vertical slice, selected coaching moments, and LLM-grounded conversation are proven useful.

- Golden PGN regression corpus
- Backend MVP usage docs
- Architecture boundary tests
- Stable CLI demo output

## Phase 11 — Product-Facing Vertical Slice

Make the app feel usable before expanding detector breadth.

- Real LLM provider adapter
- Backend LLM CLI demo
- Minimal backend API
- Minimal Vite React frontend
- Board and position viewer
- Product demo polish

This phase proves:

```text
PGN input -> backend analysis -> selected coaching evidence -> real LLM answer -> simple UI
```

## Phase 12 — Detector Expansion

Add more chess concepts only after the product-facing vertical slice exists.

- Detector expansion readiness
- LoosePieceDetector, if selected
- PinDetector, if selected
- SkewerDetector, BackRankWeaknessDetector, PassedPawnDetector, or pawn structure foundations

## Later

These should wait until the product-facing vertical slice is useful.

- persistence/database for user history
- auth
- deployment
