# Coaching Moment Selection

## Purpose

The detector and verification layers can legitimately produce many `VerifiedEvent` objects for one game. That raw volume is useful for debugging, pattern aggregation, retrieval, drill generation, and future coaching features, but it is too noisy to show directly as the main user-facing review.

The intended distinction is:

```text
VerifiedEvent = raw verified evidence
CoachingMoment = selected teaching point
```

The system keeps all raw verified events in pipeline outputs, then selects a small number of coaching moments for review.

## Principles

1. Detectors identify chess motifs. They do not decide what is worth coaching.
2. Engine verification measures objective impact. It preserves raw engine evidence and computes a canonical event impact.
3. Coaching selection happens after verification, using `VerifiedEvent` objects and event metadata.
4. The selector reduces noise without deleting raw evidence from `GameAnalysisResult.verified_events`.
5. The LLM coach should receive retrieved or selected evidence, not an unfiltered dump of every raw event by default.

## Event Type Metadata

Event types need central metadata that describes their downstream coaching meaning.

Examples:

```text
fork_created              -> positive, tactics, actual_move, execution_strength
knight_outpost_created    -> positive, positional, actual_move, execution_strength
fork_missed               -> negative, tactics, missed_candidate
fork_allowed              -> negative, tactics, allowed_response
hanging_piece_created     -> negative, piece_safety, actual_move
hanging_piece_ignored     -> negative, piece_safety, actual_move
hanging_piece_lost        -> negative, piece_safety, actual_move
knight_outpost_missed     -> negative, positional, missed_candidate
```

This metadata should live in the event type metadata registry, not in individual detectors and not as scattered hardcoded lists.

## Engine Impact Fields

Raw Stockfish centipawn scores are stored from White's perspective. This is important objective evidence, but it is not enough for coaching selection.

`EngineAssessment.eval_delta` remains the raw White-perspective actual-move delta:

```text
eval_delta = eval_after - eval_before
```

`EngineAssessment.eval_delta_for_event_side` remains the actual played move delta from the attributed event side's perspective. It is useful for debugging actual-move events and keeping compatibility with earlier tasks.

For centipawn-only comparisons, the canonical field is:

```text
event_impact_for_side
```

Interpretation:

```text
positive event_impact_for_side -> better for the attributed side
negative event_impact_for_side -> worse for the attributed side
```

`impact_magnitude` is `abs(event_impact_for_side)` when available.

For comparisons that involve at least one mate score, the canonical fields are:

```text
event_score_kind = "mate"
event_impact_rank_for_side
impact_rank
```

`event_score_kind="mate"` means the event comparison involved at least one mate
score, including mixed centipawn-vs-mate comparisons.

Interpretation:

```text
positive event_impact_rank_for_side -> better for the attributed side
negative event_impact_rank_for_side -> worse for the attributed side
zero event_impact_rank_for_side     -> no rank change
None                                -> unavailable
```

`impact_rank` is `abs(event_impact_rank_for_side)` when available.

Rank values are internal ordering values. They are not centipawns and must never
be labeled as centipawn values in coaching output.

## Verification Kinds

Different event types represent different chess claims, so engine verification must use different comparisons.

### actual_move

The played move itself caused the event.

Examples:

```text
hanging_piece_created
hanging_piece_ignored
hanging_piece_lost
fork_created
knight_outpost_created
```

Verification compares:

```text
before_fen -> after_fen
```

For these events, `event_impact_for_side` is the actual-move delta from the event side's perspective.

For mate-aware comparisons:

```text
event_impact_rank_for_side = after_rank_for_side - before_rank_for_side
```

### missed_candidate

The player had a candidate move but did not play it.

Examples:

```text
fork_missed
knight_outpost_missed
```

Verification compares the played move against the candidate move:

```text
before position
├── actual move played    -> eval_after
└── candidate move        -> candidate_eval_after
```

For these events:

```text
event_impact_for_side = actual_after_for_event_side - candidate_after_for_event_side
```

A negative value means missing the candidate hurt the attributed side. A positive value means the candidate was worse than the move played and should not be promoted as a negative coaching moment.

For mate-aware comparisons:

```text
event_impact_rank_for_side = actual_after_rank_for_side - candidate_after_rank_for_side
```

### allowed_response

The played move allowed the opponent a dangerous candidate reply.

Example:

```text
fork_allowed
```

Verification compares the after-position against the opponent candidate reply:

```text
after actual move
└── opponent candidate reply -> candidate_eval_after
```

For these events:

```text
event_impact_for_side = candidate_after_for_event_side - actual_after_for_event_side
```

A negative value means the opponent reply would hurt the side who allowed it.

For mate-aware comparisons:

```text
event_impact_rank_for_side = candidate_after_rank_for_side - actual_after_rank_for_side
```

## Current Selection Rules

The current selector is deterministic and intentionally simple.

Rules:

1. Use centipawn `event_impact_for_side` for centipawn-only comparisons, or mate-aware `event_impact_rank_for_side` for mate comparisons.
2. Look up event type polarity from `EventTypeMetadata`.
3. Skip neutral or unknown event types.
4. Skip events with no usable centipawn impact or mate-aware rank impact.
5. Filter out low-impact centipawn events below the configured threshold, currently defaulting to 80 centipawns. Mate events use rank impact and are not compared to centipawn thresholds.
6. Filter out polarity-mismatched events:
   - positive event type but canonical signed impact is not positive
   - negative event type but canonical signed impact is not negative
7. Rank selected events by mate-aware `impact_rank` first, then centipawn `impact_magnitude`, with deterministic tie-breakers.
8. Limit the review to a small number of moments, currently defaulting to top 5.

## Coaching Relevance Policy

The selection rules above are shared by user-facing review selection and
user-facing weakness profile construction through `CoachingRelevancePolicy`.

This policy is intentionally chess-agnostic. It does not inspect legal moves,
call `FeatureStore`, call Stockfish, or create new chess facts. It only reads
already verified evidence:

```text
VerifiedEvent.event.event_type
EngineAssessment.event_impact_for_side
EngineAssessment.impact_magnitude
EngineAssessment.event_score_kind
EngineAssessment.event_impact_rank_for_side
EngineAssessment.impact_rank
EventTypeMetadata.polarity
```

Raw aggregation remains raw:

```text
PatternAggregator -> raw/debug DetectedPattern objects
WeaknessProfileBuilder -> profile-local relevance-filtered DetectedPattern objects
```

`GameAnalysisResult.detected_patterns` is not mutated or filtered. It remains
useful for debugging and future evidence retrieval. `WeaknessProfile` contains
relevant positive or negative profile-local patterns plus separate execution
strength patterns.

Profile-local pattern fields are recomputed from filtered supporting events:

- `frequency`: number of relevant supporting events
- `severity`: average centipawn `impact_magnitude` for centipawn events or average mate-aware `impact_rank` for mate events
- `supporting_events`: the relevant supporting events in original order

Neutral or unknown event types are excluded from user-facing strengths,
weaknesses, and recurring themes. They remain available in raw detected
patterns if the raw aggregator produced them.

## Evidence Retrieval Ranking

Retrieval is broader than coaching selection. `EvidenceRetriever.retrieve_events()`
does not filter by coaching relevance, event polarity, or thresholds. It keeps
raw verified events available for debugging, prompts, and future tools.

Event retrieval is ordered by canonical verified evidence strength:

1. Mate-aware events with `impact_rank`, ranked before centipawn-impact events.
2. Centipawn and candidate-aware events with `impact_magnitude`.
3. Detector `severity` only when no canonical verified impact is available.

Retrieval must not sort raw events by `eval_delta`. `eval_delta` is raw
White-perspective actual-move evidence, so it is not the right importance signal
for missed-candidate, allowed-response, or mate-aware events.

This ordering is not relevance filtering. Low-impact, polarity-mismatched,
neutral, and unknown events may still be returned by retrieval if they match the
caller filters. User-facing review selection remains the responsibility of
`CoachingRelevancePolicy` and `CoachingMomentSelector`.

## Execution Strength Evidence

Strengths and weaknesses are not perfectly symmetric. A weakness usually means
the player made or missed something engine-important. A strength can also mean
the player successfully executed a detected motif after the opportunity already
existed, so the immediate engine swing may be small.

`ExecutionStrengthPolicy` handles this second case. It is intentionally
metadata-and-assessment-only. It does not inspect legal moves, call
`FeatureStore`, call Stockfish, or create chess facts.

Execution strength rules:

1. Event type polarity must be positive.
2. `EventTypeMetadata.is_execution_strength` must be true.
3. The event must not be contradicted by engine evidence:
   - centipawn events require `event_impact_for_side >= 0`
   - mate events require `event_impact_rank_for_side >= 0`
   - unavailable score kind is rejected
4. No centipawn threshold is applied.
5. Events that already pass `CoachingRelevancePolicy` remain in impact
   `strengths` and are not duplicated into `execution_strengths`.

Current execution-strength event types:

- `fork_created`
- `knight_outpost_created`

`WeaknessProfile.execution_strengths` is structured evidence for successful
execution, not proof of a large engine swing. Its pattern severity is an
ordering score based on frequency, not centipawns or mate-rank impact.

## Current Grouping Behavior

User-facing grouping is currently disabled.

Each selected `VerifiedEvent` becomes one `CoachingMoment`. Internally, `CoachingMomentSelector` may still return a `VerifiedEventGroup` wrapper for compatibility, but each returned group should contain exactly one event.

Current behavior:

```text
1 selected VerifiedEvent -> 1 CoachingMoment
```

This makes CLI output easier to inspect and avoids hiding weak or noisy candidate events inside broad summaries such as:

```text
Move 16: Multiple fork-related tactical issues
```

The raw events remain available separately in `GameAnalysisResult.verified_events`.

## Known Limitations

Positive execution events such as `fork_created` may have low immediate engine
impact because the evaluation often changed when the opponent allowed the
tactic, not when the player executed it. Execution strengths surface these
events without artificially boosting their engine impact. Full tactical sequence
or narrative linking is still deferred.

Mate scores are now represented as structured scores and internal rank values.
Those rank values are not centipawns. Future prompt and UI work must describe
mate outcomes as mate outcomes, not as synthetic centipawn swings.

## Future Grouping Design

Grouping may return later after candidate-aware verification and output quality are stable.

A future grouping implementation should only group events that clearly represent the same underlying lesson. It should avoid merging weak candidate events into an authoritative-looking summary.

Possible future grouping key:

```text
metadata.ply + event.side + event category + event polarity + event type
```

Good future grouping:

```text
Move 16: multiple missed fork candidates
supporting evidence:
- fork_missed on e6
- fork_missed on g7
```

Bad grouping:

```text
Move 16: fork created and queen hung
```

Positive and negative events should not be merged into a single celebratory or corrective moment without careful explanation.

## Output Goal

A noisy game might produce:

```text
129 VerifiedEvents
```

but the review should produce something closer to:

```text
5 selected CoachingMoments
```

The raw events remain available for:

- debugging
- pattern aggregation
- drill generation
- detailed evidence retrieval
- LLM grounding

The selected coaching moments become the primary user-facing review.

## Relationship To The LLM

The LLM is not responsible for selecting chess facts or deciding whether a tactic exists.

The LLM should receive selected evidence such as:

```text
Top coaching moments
Recurring patterns
Weakness profile
Representative verified events
```

It should not receive raw PGNs or an unfiltered dump of every detector event by default.

This keeps the LLM as a communicator and teacher over verified evidence, not as the chess analysis engine.

## Provider-Agnostic Prompt Boundary

`PromptBuilder` creates deterministic `LLMPrompt` objects from structured
evidence only. The prompt has separate `system` and `user` fields so future
provider clients can map them to provider-specific message formats without
changing coaching evidence construction.

The prompt builder accepts:

- user question
- selected coaching moments
- retrieved verified events
- retrieved or profile-relevant detected patterns
- weakness profile data, including execution strengths

It does not accept raw PGN text as evidence. The user question may contain
ordinary chess notation, but the system instructions tell the LLM not to analyze
raw PGNs, FENs, or unsupported chess claims.

Task 27 does not add a real provider, network call, API key handling,
conversation memory, streaming, or LLM chat orchestration. Those remain future
coaching-layer tasks.

## LLM Chat Coach Orchestration

`LLMChatCoach` is the first LLM-facing conversational coach wrapper. It does
not retrieve evidence and does not perform chess analysis. Callers provide the
already selected or retrieved evidence, and `LLMChatCoach`:

1. delegates prompt construction to `PromptBuilder`
2. sends the resulting `LLMPrompt` to an injected `LLMClient`
3. returns the generated response

The injected client is provider-agnostic. Real provider adapters, API keys, CLI
wiring, memory, streaming, and retrieval orchestration remain future tasks.

The full LLM grounding policy is documented in `docs/LLM_GROUNDING.md`. Future
provider adapters must preserve that boundary: the LLM explains selected or
retrieved evidence, but it does not analyze raw PGNs, calculate moves, verify
tactics, or invent unsupported chess claims.
