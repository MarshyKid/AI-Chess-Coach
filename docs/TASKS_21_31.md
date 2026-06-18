# Tasks 21-30 — Backend MVP And Evidence-Grounded Coaching Roadmap

This file supersedes the older `docs/TASKS_21_30.md` roadmap for the current backend-first phase.

Tasks 21-30 are complete. The next product-facing phase is documented in
`docs/TASKS_31_40.md`. Detector expansion is intentionally deferred until after
real LLM provider integration, a minimal API, and a minimal frontend vertical
slice exist.

The goal is to keep the project moving one task at a time while preserving the core architecture rule:

```text
PGN → Replay → MoveTransition → FeatureStore → Detector → DetectedEvent → EngineAssessment → VerifiedEvent → PatternAggregation → WeaknessProfile → Retrieval/Coaching → LLM explains evidence only
```

The LLM must not do chess correctness. Chess correctness comes from deterministic detectors plus engine verification.

---

## Current Project State

Tasks 1-30 are complete and accepted.

The current backend can:

- load and replay PGNs
- build `MoveTransition` objects
- run detectors through the detector pipeline
- produce `DetectedEvent` objects
- verify events with Stockfish through the engine layer
- compute candidate-aware event impact for missed and allowed events
- aggregate patterns
- build a relevance-filtered user-facing weakness profile
- select coaching moments
- retrieve verified events using canonical mate/candidate-aware impact ranking
- build provider-agnostic grounded prompts from structured evidence
- answer through an injected provider-agnostic LLM client using grounded prompts
- protect the LLM boundary with grounding tests and documentation
- print a backend-only CLI review
- run a small golden PGN regression corpus for backend MVP readiness

Implemented detectors:

- `HangingPieceDetector`
- `ForkDetector`
- `KnightOutpostDetector`

---

## Task 21 — End-to-End Game Analysis Pipeline

Status: complete and accepted

Goal:

Create `GameAnalysisPipeline` to orchestrate PGN replay, detection, verification, pattern aggregation, weakness profiling, and review generation.

Important outcome:

`GameAnalysisResult` preserves all raw pipeline outputs, including raw `verified_events` and selected `coaching_moments`.

---

## Task 22 — CLI Demo For PGN File Analysis

Status: complete and accepted

Goal:

Add a backend-only CLI command for analyzing a PGN file.

Important outcome:

`ai-chess-coach-analyze <file.pgn>` prints detected events, verified events, patterns, weakness profile, and coaching moments.

Rules:

- CLI orchestrates the pipeline only.
- CLI must not perform chess analysis itself.
- CLI must not call LLMs.

---

## Task 23 — Event Metadata Refactor

Status: complete and accepted

Goal:

Replace stringly typed FEN and move metadata conventions with `EventMetadata`.

Important outcome:

`DetectedEvent.metadata` stores:

- `before_fen`
- `after_fen`
- `move_uci`
- `move_san`
- `ply`

---

## Task 24 — Event Type Metadata And Polarity Registry

Status: complete and accepted

Goal:

Centralize event type meaning in `EventTypeMetadata`.

Important outcome:

The registry classifies event types by:

- `event_type`
- `display_name`
- `category`
- `polarity`

Unknown event types are deterministic and neutral.

---

## Task 25 — Side-Aware Engine Impact

Status: complete and accepted

Goal:

Preserve raw White-perspective engine deltas while computing side-aware impact for the attributed event side.

Important outcome:

`EngineAssessment` includes:

- `eval_delta_for_event_side`
- `impact_magnitude`

`eval_delta` remains raw White-perspective actual-move delta.

---

## Task 26 — Coaching Moment Selection

Status: complete and accepted, later refined by Tasks 26C and 26D

Goal:

Convert many verified events into a smaller number of useful coaching moments by filtering low-impact events, respecting event polarity, and limiting output to the most teachable moments.

Important outcome:

`CoachingMomentSelector` filters events before `ReviewGenerator` creates user-facing `CoachingMoment` objects.

Original grouping behavior was later disabled by Task 26C.

---

## Task 26B — Summary And Detail Rendering For Coaching Moments

Status: complete and accepted

Goal:

Make selected coaching moment output clearer while preserving raw verified evidence.

Important outcome:

`coaching/evidence_formatter.py` formats one deterministic detail line per supporting event.

CLI coaching moments now print:

- title
- position
- highlights
- summary
- details

No detector semantics, selection logic, engine behavior, or LLM behavior changed in this task.

---

## Task 26C — Individual Coaching Moment Selection

Status: complete and accepted

Goal:

Temporarily remove user-facing grouping so each selected `VerifiedEvent` becomes its own `CoachingMoment`.

Reason:

Grouping same-ply events made debugging difficult and could hide noisy candidate events under broad summaries like:

```text
Move 16: Multiple fork-related tactical issues
```

Important outcome:

Each selected group currently contains exactly one `VerifiedEvent`.

Current behavior:

```text
1 selected VerifiedEvent -> 1 CoachingMoment
```

Rules preserved:

- skip neutral or unknown events
- skip missing impact
- skip low-impact events
- filter polarity mismatches
- sort by impact magnitude
- limit to top moments

---

## Task 26D — Verification Strategy And Candidate-Aware Engine Impact

Status: complete and accepted

Goal:

Refactor engine verification so actual-move, missed-candidate, and allowed-response events get engine evidence that matches what the event represents.

Problem fixed:

Previously, `fork_missed` events inherited the actual move's eval delta. A bad fork-shaped candidate could look like a meaningful missed tactic if the actual move had a large eval swing.

Important model changes:

- `CandidateMove`
- `DetectedEvent.candidate_move`
- `EventTypeMetadata.verification_kind`
- `EngineAssessment.candidate_eval_after`
- `EngineAssessment.candidate_move_uci`
- `EngineAssessment.candidate_after_fen`
- `EngineAssessment.event_impact_for_side`

Verification kinds:

```text
actual_move       -> before_fen vs after_fen
missed_candidate  -> actual_after vs candidate_after from before_fen
allowed_response  -> actual_after vs opponent candidate_after from after_fen
```

Canonical coaching field:

```text
event_impact_for_side
```

Selector behavior:

- positive event types require `event_impact_for_side > 0`
- negative event types require `event_impact_for_side < 0`
- `impact_magnitude = abs(event_impact_for_side)` when available

Rules:

- Detectors still do not call Stockfish.
- Engine verifier remains the only Stockfish boundary.
- Selector remains chess-agnostic.
- Review/LLM explain verified evidence only.

---

## Task 26E — Shared Coaching-Relevance Filtering

Status: complete and accepted after implementation

Dependencies:

- Task 26D

Goal:

Use one shared relevance policy for coaching moment selection and user-facing
weakness profile construction.

Problem fixed:

Raw pattern aggregation can contain geometrical or debug events that are not
engine-relevant, have missing impact, are below the coaching threshold, or do
not match event polarity. Those raw events should remain available, but they
should not make the user-facing profile claim a recurring weakness or strength.

Important outcome:

`GameAnalysisResult.detected_patterns` remains raw/debug output.

`WeaknessProfile` is built from profile-local `DetectedPattern` objects whose
supporting events pass `CoachingRelevancePolicy`.

Shared relevance rules:

- skip neutral or unknown event types
- skip missing centipawn impact or mate-aware rank impact
- skip centipawn events below the configured impact threshold
- positive events require canonical signed impact greater than zero
- negative events require canonical signed impact less than zero

Profile-local pattern recomputation:

- `frequency` is the count of filtered supporting events
- `severity` is the average centipawn `impact_magnitude` or mate-aware `impact_rank`
- `supporting_events` preserves filtered supporting events in original order

Known limitations:

- Positive execution events like `fork_created` can still be underrepresented
  when their immediate engine impact is low. Task 26H adds separate execution
  strength evidence without changing impact relevance. Full tactical sequence
  and narrative linking are deferred.

Rules:

- Do not mutate raw detected patterns.
- Do not change detector semantics or event type names.
- Do not change engine verification.
- Do not add tactical sequence linking in this task.
- Do not add LLM calls, frontend, API, database, auth, deployment, or new detectors.

---

## Task 26G — Mate-Aware Engine Assessment

Status: complete and accepted after implementation

Dependencies:

- Task 26D
- Task 26E

Goal:

Preserve mate scores as first-class engine evidence and make selection/profile
ranking work for centipawn, mate, and mixed centipawn-vs-mate comparisons.

Important outcome:

`EngineScore` stores one of:

- centipawns
- mate
- unavailable

Internal rank formula:

```text
centipawns      -> centipawns
mate > 0        -> 10_000_000 - abs(mate)
mate < 0        -> -10_000_000 + abs(mate)
mate == 0       -> 10_000_000
unavailable     -> None
```

Rank values are internal ordering values. They are not centipawns and must not
be displayed as centipawn values.

`EngineAssessment` includes:

- `score_before`
- `score_after`
- `candidate_score_after`
- `event_score_kind`
- `event_impact_rank_for_side`
- `impact_rank`

`event_score_kind="mate"` means the event comparison involved at least one mate
score.

Rank impact formulas:

```text
actual_move       -> after_rank_for_side - before_rank_for_side
missed_candidate  -> actual_after_rank_for_side - candidate_after_rank_for_side
allowed_response  -> candidate_after_rank_for_side - actual_after_rank_for_side
```

Sign semantics:

- positive `event_impact_rank_for_side`: improved the attributed side's position
- negative `event_impact_rank_for_side`: worsened the attributed side's position
- zero: no rank change
- `None`: unavailable

Selection behavior:

- centipawn comparisons use `event_impact_for_side` and `impact_magnitude`
- mate comparisons use `event_impact_rank_for_side` and `impact_rank`
- selector and profile builder remain metadata/rank-only and chess-analysis-free

Rules:

- Do not change detector semantics or event type names.
- Do not add synthetic centipawn display for mate scores.
- Do not add LLM calls, frontend, API, database, auth, deployment, or new detectors.

---

## Task 26H — Positive Execution And Strength Profile Semantics

Status: complete and accepted after implementation

Dependencies:

- Task 26E
- Task 26G

Goal:

Surface positive execution evidence separately from high-impact strengths so
the profile can show successful motif execution without pretending it caused a
large engine swing.

Problem fixed:

Low-impact `fork_created` and `knight_outpost_created` events could disappear
from user-facing strengths because the same impact threshold was used for
mistakes and strengths.

Important outcome:

`EventTypeMetadata` includes:

- `is_execution_strength`

Current execution-strength event types:

- `fork_created`
- `knight_outpost_created`

`WeaknessProfile` includes:

- `execution_strengths`

`ExecutionStrengthPolicy` accepts positive execution events when engine evidence
does not contradict them:

- centipawn events require `event_impact_for_side >= 0`
- mate events require `event_impact_rank_for_side >= 0`
- unavailable score kind is rejected

Profile behavior:

- `strengths` remains impact/high-impact strengths.
- `execution_strengths` contains low-impact positive execution patterns.
- `weaknesses` remains impact-filtered.
- `recurring_themes` remains the impact-filtered union.
- Raw `GameAnalysisResult.detected_patterns` remains raw/debug output.

Execution-strength pattern severity is `float(frequency)`. It is an ordering
score only, not centipawns or mate-rank impact.

Rules:

- Do not artificially boost engine impact or mate rank.
- Do not change detector semantics or event type names.
- Do not change engine verification.
- Do not implement tactical sequence linking.
- Do not add LLM calls, frontend, API, database, auth, deployment, or new detectors.

---

## Task 26I — Mate/Candidate-Aware Evidence Retrieval Ranking

Status: complete and accepted after implementation

Dependencies:

- Task 26D
- Task 26G

Goal:

Rank raw retrieved `VerifiedEvent` objects by canonical verified impact instead
of raw White-perspective actual-move `eval_delta`.

Important outcome:

`EvidenceRetriever.retrieve_events()` remains broad and non-filtering. It does
not apply `CoachingRelevancePolicy`, classify strengths or weaknesses, or hide
raw evidence. It only orders matching verified events deterministically.

Event retrieval priority:

1. Mate-aware events with `impact_rank`.
2. Centipawn and candidate-aware events with `impact_magnitude`.
3. Detector `severity` only when canonical verified impact is unavailable.

Tie-breakers:

- metadata ply ascending
- event type ascending
- move UCI ascending
- squares tuple ascending

Rules:

- Do not use raw `eval_delta` for retrieval ordering.
- Do not change pattern or profile retrieval behavior.
- Do not import or call relevance policy from retrieval.
- Do not change detector semantics, event type names, engine verification,
  mate scoring, selector behavior, or profile-builder behavior.
- Do not add LLM calls, frontend, API, database, auth, deployment, or new
  detectors.

---

## Task 27 — LLM Client And Prompt Builder

Status: complete and accepted after implementation

Dependencies:

- Tasks 21-26I

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

- `LLMClient` protocol or abstraction
- `PromptBuilder` for evidence-grounded coaching prompts
- immutable `LLMPrompt` value object with separate `system` and `user` fields

Acceptance criteria:

- Prompt builder accepts selected structured evidence only, such as:
  - user question
  - retrieved verified events
  - detected patterns
  - weakness profile data
  - selected coaching moments
- Prompt explicitly instructs the LLM to use only supplied evidence.
- Prompt explicitly forbids raw chess analysis, move calculation, and unsupported claims.
- Prompt treats selected coaching moments as the primary user-facing teaching points.
- Prompt includes weakness profile execution strengths when supplied.
- Prompt distinguishes centipawn impact from mate-aware rank impact.
- LLM client can be mocked in tests.
- Tests pass.

Rules / non-goals:

- Do not call a real LLM in unit tests.
- Do not send raw PGNs to the LLM.
- Do not ask the LLM to analyze chess positions.
- Do not add provider SDK dependencies, API key handling, CLI wiring,
  conversation memory, streaming, or retrieval orchestration.
- Do not call Stockfish.
- Do not add frontend, database, auth, deployment, or persistence.

---

## Task 28 — LLM-Grounded Conversational Coach

Status: complete and accepted after implementation

Dependencies:

- Task 27

Goal:

Create the first evidence-grounded AI coach that can answer player questions conversationally using retrieved and selected evidence.

Files to create or update:

```text
src/ai_chess_coach/coaching/llm_chat_coach.py
tests/coaching/test_llm_chat_coach.py
```

Acceptance criteria:

- Accepts a user question and retrieved or selected evidence.
- Uses `PromptBuilder` to construct a grounded prompt.
- Calls an injected `LLMClient` abstraction.
- Returns the LLM response.
- Tests use a fake or mock LLM client.
- Tests verify selected coaching moments and retrieved evidence are included in the prompt.
- Tests verify raw PGNs are rejected or not accepted.
- Empty evidence is allowed and remains grounded through the prompt builder.
- Client exceptions propagate until real provider adapters define a shared error model.

Rules / non-goals:

- LLM must not receive raw PGNs.
- LLM must not replace detectors.
- LLM must not call Stockfish.
- LLM must not perform direct chess analysis.
- LLM should explain and synthesize retrieved or selected evidence only.
- No concrete provider SDK, API key handling, CLI wiring, retrieval
  orchestration, memory, streaming, or embeddings.
- No frontend, database, auth, deployment, or persistence.

---

## Task 29 — LLM Grounding And Safety Tests

Status: complete and accepted after implementation

Dependencies:

- Task 28

Goal:

Add guardrail tests that protect the product architecture before adding more detectors or frontend work.

Files to create or update:

```text
tests/coaching/test_llm_grounding.py
docs/LLM_GROUNDING.md
```

Acceptance criteria:

- Tests verify prompts include retrieved evidence.
- Tests verify prompts include selected coaching moments rather than dumping all raw events by default.
- Tests verify prompts instruct the LLM not to analyze raw PGNs.
- Tests verify prompts instruct the LLM not to invent unsupported chess claims.
- Tests verify prompts distinguish evidence from user question text.
- Documentation explains that the LLM is a communicator, not the chess analysis engine.
- Tests verify prompt-injection-like question text does not remove grounding instructions.
- Tests verify PGN/FEN-looking question text remains question text, not verified evidence.
- Tests verify runtime LLM modules remain free of engine, detector, provider, and network imports.

Rules / non-goals:

- Do not call a real LLM in tests.
- Do not add prompt evaluation infrastructure beyond simple deterministic tests.
- Do not add frontend, persistence, auth, or deployment.

---

## Task 30 — Golden PGN Regression Corpus And Backend MVP Readiness

Status: complete and accepted after implementation

Dependencies:

- Tasks 21-29

Goal:

Harden the backend MVP after the vertical slice, event selection, candidate-aware verification, and LLM-grounded conversation loop are in place.

Files to create or update:

```text
tests/fixtures/pgns/*.pgn
tests/pipeline/test_golden_pgns.py
docs/TESTING.md
docs/MVP_USAGE.md
```

Acceptance criteria:

- Full pipeline produces stable outputs for representative games covering:
  - hanging pieces
  - forks
  - outposts
- Tests verify noisy raw events are reduced to selected coaching moments.
- Tests verify selected coaching moments are side-aware, polarity-aware, and candidate-aware.
- One documented command analyzes a PGN file end-to-end.
- Tests verify detectors remain engine-free.
- Tests verify coaching remains evidence-grounded.
- Tests verify LLM calls, if configured, use selected or retrieved evidence only.

Rules / non-goals:

- Do not add frontend.
- Do not add database or persistence.
- Do not add auth.
- Do not add deployment.
- Do not add additional detectors in this task.

---

## Deferred Detector Expansion Note

Status: deferred until after product-facing vertical slice

Dependencies:

- Task 36 from `docs/TASKS_31_40.md`
- `docs/ADDING_DETECTORS.md`

Goal:

Prepare for adding new detectors without weakening architecture boundaries or duplicating chess logic.

Important update:

Detector expansion is not the immediate next priority after Task 30. The current
detector set is sufficient for a working MVP demo. The next milestone is:

```text
PGN input -> backend analysis -> selected coaching evidence -> real LLM answer -> simple UI
```

Use `docs/TASKS_31_40.md` for the current next task sequence. The current
Task 31 is now `Real LLM Provider Adapter`, not detector expansion.

Candidate future detectors:

- `LoosePieceDetector`
- `PinDetector`
- `SkewerDetector`
- `BackRankWeaknessDetector`
- pawn structure foundations
- `PassedPawnDetector`
- more advanced motif detectors

Recommended process:

1. Read `docs/ADDING_DETECTORS.md`.
2. Add one detector at a time.
3. Define event types before coding.
4. Register event metadata, including polarity and verification kind.
5. Decide whether events are actual-move, missed-candidate, or allowed-response.
6. Add typed `CandidateMove` only for counterfactual events.
7. Add detector tests before expanding review behavior.
8. Keep detectors deterministic, engine-free, and LLM-free.

Rules / non-goals:

- Do not add multiple detectors in one task.
- Do not make detectors call Stockfish.
- Do not make detectors generate coaching prose.
- Do not bypass `FeatureStore` when reusable features exist.
- Do not make selector or review code perform chess analysis.
- Do not add frontend, database, auth, deployment, or persistence as part of detector work.

---

## Later

These remain intentionally deferred until the product-facing vertical slice is useful:

- More detectors
- Persistence/database for user history
- Auth
- Deployment
