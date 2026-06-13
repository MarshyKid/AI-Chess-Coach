# Tasks 21-30 — Post-Task-20 Roadmap Extension

This file extends the implementation plan after `docs/TASKS.md` Task 20.

The goal is to reach a useful vertical-slice MVP first, then introduce the LLM-grounded conversational coach early because conversation with the AI coach is a key product feature. Additional detectors come after the core evidence-to-conversation loop works.

---

## Task 21 — End-to-End Game Analysis Pipeline

Status: [ ]

Dependencies:

* Task 20

Goal:

Orchestrate the existing backend pieces into one deterministic PGN-to-coaching pipeline.

Files to create or update:

```text
src/ai_chess_coach/pipeline/__init__.py
src/ai_chess_coach/pipeline/game_analysis_pipeline.py
src/ai_chess_coach/models/game_analysis_result.py
tests/pipeline/test_game_analysis_pipeline.py
```

Deliverables:

* `GameAnalysisPipeline`
* `GameAnalysisResult`

Acceptance Criteria:

* Loads PGN text.
* Replays moves into `MoveTransition` objects.
* Runs registered detectors through the detector pipeline.
* Verifies detected events through `EventVerifier`.
* Aggregates verified events into detected patterns.
* Builds a weakness profile.
* Generates coaching moments.
* Returns all structured outputs in a `GameAnalysisResult`.
* Tests pass.

Rules / Non-Goals:

* No CLI in this task.
* No frontend.
* No database or persistence.
* No LLM calls.
* No raw-PGN-to-LLM shortcut.
* No detector logic inside the pipeline.
* The pipeline orchestrates existing components; it does not replace them.

---

## Task 22 — CLI Demo For PGN File Analysis

Status: [ ]

Dependencies:

* Task 21

Goal:

Provide a local backend-only demo that analyzes a PGN file and prints structured review output.

Files to create or update:

```text
src/ai_chess_coach/cli/__init__.py
src/ai_chess_coach/cli/analyze_pgn.py
tests/cli/test_analyze_pgn.py
pyproject.toml
```

Deliverables:

* CLI entry point, such as `uv run ai-chess-coach-analyze <file.pgn>` or `uv run python -m ai_chess_coach.cli.analyze_pgn <file.pgn>`.

Acceptance Criteria:

* Reads a PGN file from disk.
* Invokes `GameAnalysisPipeline`.
* Prints detected events, verified events, detected patterns, weakness profile summary, and coaching moments.
* Exits clearly when Stockfish is unavailable.
* Tests pass.

Rules / Non-Goals:

* CLI must not perform chess analysis itself.
* CLI must not call detectors directly outside the pipeline.
* No persistence.
* No frontend.
* No LLM calls.

---

## Task 23 — Event Metadata Refactor

Status: [ ]

Dependencies:

* Task 21

Goal:

Replace important stringly typed evidence conventions like `before_fen` and `after_fen` with typed event metadata.

Files to create or update:

```text
src/ai_chess_coach/models/detected_event.py
src/ai_chess_coach/models/event_metadata.py
tests/models/test_detected_event.py
tests/models/test_event_metadata.py
tests/detectors/test_hanging_piece_detector.py
tests/detectors/test_fork_detector.py
tests/detectors/test_knight_outpost_detector.py
tests/engine/test_verifier.py
tests/coaching/test_review_generator.py
```

Deliverables:

* `EventMetadata` model.
* Updated `DetectedEvent` model that exposes typed metadata.

Acceptance Criteria:

* Events expose typed metadata for:
  * `before_fen`
  * `after_fen`
  * `move_uci`
  * `move_san`
  * `ply`
* Verifier and review code no longer depend on stringly typed FEN evidence.
* Existing detectors still produce the same event types.
* Tests pass.

Rules / Non-Goals:

* Do not change detector semantics.
* Do not change event type names.
* Do not generate coaching text in detectors.
* Do not change engine behavior.
* Do not introduce LLM calls.

---

## Task 24 — LLM Client And Prompt Builder

Status: [ ]

Dependencies:

* Task 22
* Task 23

Goal:

Prepare the LLM integration boundary without letting the LLM perform chess analysis.

Files to create or update:

```text
src/ai_chess_coach/coaching/llm_client.py
src/ai_chess_coach/coaching/prompt_builder.py
tests/coaching/test_llm_client.py
tests/coaching/test_prompt_builder.py
```

Deliverables:

* `LLMClient` protocol or abstraction.
* `PromptBuilder` for evidence-grounded coaching prompts.

Acceptance Criteria:

* Prompt builder accepts existing structured evidence only, such as:
  * user question
  * retrieved verified events
  * detected patterns
  * weakness profile data
  * coaching moments
* Prompt explicitly instructs the LLM to use only supplied evidence.
* Prompt explicitly forbids raw chess analysis, move calculation, and unsupported claims.
* LLM client can be mocked in tests.
* Tests pass.

Rules / Non-Goals:

* Do not call a real LLM in unit tests.
* Do not send raw PGNs to the LLM.
* Do not ask the LLM to analyze chess positions.
* Do not call Stockfish.
* Do not add frontend, database, auth, or deployment.

---

## Task 25 — LLM-Grounded Conversational Coach

Status: [ ]

Dependencies:

* Task 24

Goal:

Create the first evidence-grounded AI coach that can answer player questions conversationally using retrieved evidence.

Files to create or update:

```text
src/ai_chess_coach/coaching/llm_chat_coach.py
tests/coaching/test_llm_chat_coach.py
```

Deliverables:

* `LLMChatCoach`

Acceptance Criteria:

* Accepts a user question and retrieved evidence.
* Uses `PromptBuilder` to construct a grounded prompt.
* Calls the injected `LLMClient` abstraction.
* Returns the LLM response.
* Tests use a fake or mock LLM client.
* Tests verify that retrieved evidence is included in the prompt.
* Tests verify that raw PGNs are rejected or not accepted.
* Tests pass.

Rules / Non-Goals:

* LLM must not receive raw PGNs.
* LLM must not replace detectors.
* LLM must not call Stockfish.
* LLM must not perform direct chess analysis.
* LLM should explain and synthesize retrieved evidence only.
* No frontend, database, auth, or deployment.

---

## Task 26 — LLM Grounding And Safety Tests

Status: [ ]

Dependencies:

* Task 25

Goal:

Add guardrail tests that protect the product architecture before adding more detectors.

Files to create or update:

```text
tests/coaching/test_llm_grounding.py
docs/LLM_GROUNDING.md
```

Deliverables:

* LLM grounding tests.
* LLM grounding documentation.

Acceptance Criteria:

* Tests verify prompts include retrieved evidence.
* Tests verify prompts instruct the LLM not to analyze raw PGNs.
* Tests verify prompts instruct the LLM not to invent unsupported chess claims.
* Tests verify prompts distinguish evidence from user question text.
* Documentation explains that the LLM is a communicator, not the chess analysis engine.
* Tests pass.

Rules / Non-Goals:

* Do not call a real LLM in tests.
* Do not add prompt evaluation infrastructure beyond simple deterministic tests.
* Do not add frontend, persistence, auth, or deployment.

---

## Task 27 — LoosePieceDetector

Status: [ ]

Dependencies:

* Task 23

Goal:

Detect recurring loose-piece patterns that are not necessarily hanging yet.

Files to create or update:

```text
src/ai_chess_coach/detectors/loose_piece_detector.py
tests/detectors/test_loose_piece_detector.py
src/ai_chess_coach/detectors/__init__.py
```

Deliverables:

* `LoosePieceDetector`

Acceptance Criteria:

* Emits structured events such as:
  * `loose_piece_created`
  * `loose_piece_ignored`
* Uses `FeatureStore.piece_safety()`.
* Tests pass.

Rules / Non-Goals:

* Do not call Stockfish.
* Do not generate coaching text.
* Do not duplicate piece-safety logic.
* Do not modify engine verification.
* Do not call LLMs.

---

## Task 28 — PinDetector

Status: [ ]

Dependencies:

* Task 23

Goal:

Detect meaningful pin events using existing pinned-piece features.

Files to create or update:

```text
src/ai_chess_coach/detectors/pin_detector.py
tests/detectors/test_pin_detector.py
src/ai_chess_coach/detectors/__init__.py
```

Deliverables:

* `PinDetector`

Acceptance Criteria:

* Detects structured events such as:
  * `pin_created`
  * `pin_allowed`
  * `pinned_piece_exploited`
* Uses `FeatureStore.pinned_pieces()` or existing feature helpers.
* Tests pass.

Rules / Non-Goals:

* Do not call Stockfish.
* Do not call LLMs.
* Do not generate coaching prose.
* Do not duplicate pin calculation if FeatureStore already provides it.

---

## Task 29 — BackRankWeaknessDetector

Status: [ ]

Dependencies:

* Task 23

Goal:

Add a high-value king-safety detector with simple deterministic MVP rules.

Files to create or update:

```text
src/ai_chess_coach/detectors/back_rank_weakness_detector.py
tests/detectors/test_back_rank_weakness_detector.py
src/ai_chess_coach/detectors/__init__.py
```

Deliverables:

* `BackRankWeaknessDetector`

Acceptance Criteria:

* Detects structured events such as:
  * `back_rank_weakness_created`
  * `back_rank_weakness_allowed`
* Uses deterministic board facts from `FeatureStore` or newly added FeatureStore helpers if needed.
* Tests pass.

Rules / Non-Goals:

* Do not use engine eval to discover the weakness.
* Engine verification measures importance later.
* Do not call LLMs.
* Do not generate coaching prose in detectors.

---

## Task 30 — Golden PGN Regression Corpus And Backend MVP Readiness

Status: [ ]

Dependencies:

* Tasks 21-29

Goal:

Harden the backend MVP after the vertical slice, LLM-grounded conversation, and a small detector expansion are in place.

Files to create or update:

```text
tests/fixtures/pgns/*.pgn
tests/pipeline/test_golden_pgns.py
docs/TESTING.md
docs/MVP_USAGE.md
docs/TASKS_21_30.md
```

Deliverables:

* Golden PGN fixtures.
* Backend MVP usage docs.
* Architecture boundary tests where needed.

Acceptance Criteria:

* Full pipeline produces stable outputs for representative games covering:
  * hanging pieces
  * forks
  * outposts
  * loose pieces
  * pins
  * back-rank weaknesses
* One documented command analyzes a PGN file end-to-end.
* Tests verify detectors remain engine-free.
* Tests verify coaching remains evidence-grounded.
* Tests verify LLM calls, if configured, use retrieved evidence only.
* Tests pass.

Rules / Non-Goals:

* Do not add frontend.
* Do not add database or persistence.
* Do not add auth.
* Do not add deployment.
* Do not add additional detectors in this task.

---

## Later

These are intentionally deferred until the backend MVP and evidence-grounded conversation loop are useful:

* Pawn structure feature foundation.
* PassedPawnDetector.
* More advanced detectors.
* FastAPI/backend API.
* Persistence/database for user history.
* Frontend.
* Auth.
* Deployment.
