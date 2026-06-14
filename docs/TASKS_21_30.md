# Tasks 21-30 — Post-Task-20 Roadmap Extension

This file extends the implementation plan after `docs/TASKS.md` Task 20.

The goal is to reach a useful vertical-slice MVP first, then make the coaching output selective enough for an LLM-grounded conversational coach. Additional detectors come after the core evidence-to-coaching loop is useful.

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

## Task 24 — Event Type Metadata And Polarity Registry

Status: [ ]

Dependencies:

* Task 23

Goal:

Centralize metadata about event types so downstream profiling, selection, and prompting can understand whether an event is positive, negative, or neutral without hardcoded lists scattered across the codebase.

Files to create or update:

```text
src/ai_chess_coach/models/event_type_metadata.py
src/ai_chess_coach/models/__init__.py
src/ai_chess_coach/profiling/weakness_profile_builder.py
tests/models/test_event_type_metadata.py
tests/profiling/test_weakness_profile_builder.py
docs/COACHING_SELECTION.md
```

Deliverables:

* `EventTypeMetadata` model.
* Central event type metadata registry for all current event types.
* Weakness profile builder updated to use the registry instead of local positive/negative event-type sets.

Suggested model:

```python
@dataclass(frozen=True)
class EventTypeMetadata:
    event_type: str
    display_name: str
    category: str
    polarity: Literal["positive", "negative", "neutral"]
```

Current event types to classify:

* `hanging_piece_created`
* `hanging_piece_ignored`
* `hanging_piece_lost`
* `fork_created`
* `fork_missed`
* `fork_allowed`
* `knight_outpost_created`
* `knight_outpost_missed`

Acceptance Criteria:

* Every current detector event type has an `EventTypeMetadata` entry.
* Positive events currently include:
  * `fork_created`
  * `knight_outpost_created`
* Negative events currently include:
  * `hanging_piece_created`
  * `hanging_piece_ignored`
  * `hanging_piece_lost`
  * `fork_missed`
  * `fork_allowed`
  * `knight_outpost_missed`
* WeaknessProfileBuilder no longer owns separate hardcoded positive/negative event-type sets.
* Unknown event types are handled deterministically, either as neutral or recurring-only.
* Tests pass.

Rules / Non-Goals:

* Do not change detector semantics.
* Do not change event type names.
* Do not add new detectors.
* Do not change engine verification.
* Do not implement coaching-moment filtering yet.
* Do not introduce LLM calls.

---

## Task 25 — Side-Aware Engine Impact

Status: [ ]

Dependencies:

* Task 24

Goal:

Preserve raw engine evaluation from White's perspective while also computing impact from the attributed event side's perspective. This prevents positive-looking motifs from being promoted when the engine says the move was bad for the player who created them.

Files to create or update:

```text
src/ai_chess_coach/models/engine_assessment.py
src/ai_chess_coach/engine/verifier.py
tests/models/test_engine_assessment.py
tests/engine/test_verifier.py
tests/coaching/test_review_generator.py
docs/COACHING_SELECTION.md
```

Deliverables:

* Side-aware engine impact fields.
* Verifier updated to compute those fields from `DetectedEvent.side`.

Suggested fields to add:

```python
eval_delta_for_event_side: int | None
impact_magnitude: int | None
```

Definitions:

* `eval_delta` remains the raw White-perspective delta: `eval_after - eval_before`.
* `eval_delta_for_event_side` is:
  * `eval_delta` for White-attributed events.
  * `-eval_delta` for Black-attributed events.
* `impact_magnitude` is `abs(eval_delta_for_event_side)` when available.

Acceptance Criteria:

* Existing White-perspective fields remain available.
* Verifier computes side-aware deltas using `event.side`.
* Positive side-aware delta means the event improved the attributed side's position.
* Negative side-aware delta means the event worsened the attributed side's position.
* Review/ranking code can use the side-aware fields without recomputing them.
* Tests cover White-attributed and Black-attributed events.
* Tests pass.

Rules / Non-Goals:

* Do not change detector semantics.
* Do not change event type names.
* Do not add LLM calls.
* Do not add coaching-moment selection yet.
* Do not change how Stockfish is called.
* Do not hide or overwrite the raw White-perspective evaluation.

---

## Task 26 — Coaching Moment Selection

Status: [ ]

Dependencies:

* Task 24
* Task 25

Goal:

Convert many verified events into a smaller number of useful coaching moments by filtering low-impact events, respecting event polarity, grouping near-duplicate events, and limiting the review to the most teachable lessons.

Files to create or update:

```text
src/ai_chess_coach/coaching/coaching_moment_selector.py
src/ai_chess_coach/coaching/review_generator.py
src/ai_chess_coach/coaching/__init__.py
tests/coaching/test_coaching_moment_selector.py
tests/coaching/test_review_generator.py
tests/pipeline/test_game_analysis_pipeline.py
tests/cli/test_analyze_pgn.py
docs/COACHING_SELECTION.md
```

Deliverables:

* `CoachingMomentSelector`.
* Review generation that produces selected teaching points instead of one coaching moment for every verified event.

Recommended behavior:

* Keep all raw `VerifiedEvent` objects in pipeline outputs.
* Select only a limited number of coaching moments for user-facing review.
* Use event type polarity and side-aware engine impact.
* Filter low-impact events by a default threshold, such as 80 centipawns.
* Do not promote polarity-mismatched events:
  * positive event type but bad for event side
  * negative event type but not meaningfully bad for event side
* Group related events from the same move into one teaching point when they represent the same underlying lesson.
* Prefer grouping by:
  * `metadata.ply`
  * `event.side`
  * event category
  * event polarity
* Preserve all grouped events as `supporting_evidence` in the resulting `CoachingMoment`.
* Limit output to a small default number, such as top 5 moments.

Acceptance Criteria:

* A game with many verified events can produce fewer coaching moments.
* Tiny eval swings do not become standalone coaching moments by default.
* Positive events are selected only when they helped the attributed side.
* Negative events are selected only when they hurt the attributed side.
* Multiple same-move related events can become one coaching moment with multiple supporting events.
* Raw verified events and detected patterns are not discarded.
* Tests cover filtering, polarity mismatch, grouping, and limiting.
* Tests pass.

Rules / Non-Goals:

* Do not change detector semantics.
* Do not change engine behavior.
* Do not add LLM calls.
* Do not add new detectors.
* Do not remove raw event outputs from `GameAnalysisResult`.
* Do not make the selector perform chess analysis.

---

## Task 27 — LLM Client And Prompt Builder

Status: [ ]

Dependencies:

* Task 26

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

* Prompt builder accepts selected structured evidence only, such as:
  * user question
  * retrieved verified events
  * detected patterns
  * weakness profile data
  * selected coaching moments
* Prompt explicitly instructs the LLM to use only supplied evidence.
* Prompt explicitly forbids raw chess analysis, move calculation, and unsupported claims.
* Prompt treats selected coaching moments as the primary user-facing teaching points.
* LLM client can be mocked in tests.
* Tests pass.

Rules / Non-Goals:

* Do not call a real LLM in unit tests.
* Do not send raw PGNs to the LLM.
* Do not ask the LLM to analyze chess positions.
* Do not call Stockfish.
* Do not add frontend, database, auth, or deployment.

---

## Task 28 — LLM-Grounded Conversational Coach

Status: [ ]

Dependencies:

* Task 27

Goal:

Create the first evidence-grounded AI coach that can answer player questions conversationally using retrieved and selected evidence.

Files to create or update:

```text
src/ai_chess_coach/coaching/llm_chat_coach.py
tests/coaching/test_llm_chat_coach.py
```

Deliverables:

* `LLMChatCoach`

Acceptance Criteria:

* Accepts a user question and retrieved/selected evidence.
* Uses `PromptBuilder` to construct a grounded prompt.
* Calls the injected `LLMClient` abstraction.
* Returns the LLM response.
* Tests use a fake or mock LLM client.
* Tests verify that selected coaching moments and retrieved evidence are included in the prompt.
* Tests verify that raw PGNs are rejected or not accepted.
* Tests pass.

Rules / Non-Goals:

* LLM must not receive raw PGNs.
* LLM must not replace detectors.
* LLM must not call Stockfish.
* LLM must not perform direct chess analysis.
* LLM should explain and synthesize retrieved/selected evidence only.
* No frontend, database, auth, or deployment.

---

## Task 29 — LLM Grounding And Safety Tests

Status: [ ]

Dependencies:

* Task 28

Goal:

Add guardrail tests that protect the product architecture before adding more detectors or frontend work.

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
* Tests verify prompts include selected coaching moments rather than dumping all raw events by default.
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

## Task 30 — Golden PGN Regression Corpus And Backend MVP Readiness

Status: [ ]

Dependencies:

* Tasks 21-29

Goal:

Harden the backend MVP after the vertical slice, event selection, and LLM-grounded conversation loop are in place.

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
* Regression tests for event counts, selected coaching moments, and architecture boundaries.

Acceptance Criteria:

* Full pipeline produces stable outputs for representative games covering:
  * hanging pieces
  * forks
  * outposts
* Tests verify noisy raw events are reduced to selected coaching moments.
* Tests verify selected coaching moments are side-aware and polarity-aware.
* One documented command analyzes a PGN file end-to-end.
* Tests verify detectors remain engine-free.
* Tests verify coaching remains evidence-grounded.
* Tests verify LLM calls, if configured, use selected/retrieved evidence only.
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

* LoosePieceDetector.
* PinDetector.
* BackRankWeaknessDetector.
* Pawn structure feature foundation.
* PassedPawnDetector.
* More advanced detectors.
* FastAPI/backend API.
* Persistence/database for user history.
* Frontend.
* Auth.
* Deployment.
