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

## Phase 9 — LLM-Grounded Conversational Coach

Introduce the key product experience: a player can have a conversation with an AI coach. The LLM is allowed to explain and synthesize retrieved evidence, but it must not replace detectors, Stockfish verification, or direct chess analysis.

- LLM client abstraction
- prompt builder over retrieved evidence
- LLM-grounded coach
- grounding and safety tests

## Phase 10 — Detector Expansion And MVP Hardening

After the vertical slice and LLM-grounded conversation are proven, expand chess coverage and harden the backend.

- LoosePieceDetector
- PinDetector
- BackRankWeaknessDetector
- Golden PGN regression corpus
- Backend MVP readiness pass

## Later

These should wait until the backend MVP and evidence-grounded coaching loop are useful.

- Pawn structure feature foundation
- PassedPawnDetector
- more advanced detectors
- FastAPI/backend API
- persistence/database for user history
- frontend
- auth
- deployment
