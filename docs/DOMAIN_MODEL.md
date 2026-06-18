# DOMAIN_MODEL.md

# Domain Model

This document defines the core data objects used by the AI Chess Coach backend.

These objects are intentionally separated into three categories:

1. Analysis objects
2. Verification objects
3. Coaching objects

Chess correctness must come from structured analysis and engine verification, not from LLM-generated reasoning.

---

# Design Rules

## Rule 1 — Domain Models Are Data Objects

Domain models should primarily represent structured data.

They should not:

- call Stockfish
- call LLMs
- access databases
- perform I/O
- generate coaching text unless explicitly defined as a coaching model

---

## Rule 2 — Analysis And Coaching Stay Separate

Machine-facing analysis objects must not contain user-facing coaching language.

Examples:

Good:

```text
hanging_piece_created
```

Bad:

```text
You should have defended your bishop.
```

---

## Rule 3 — Prefer Dataclasses

Use dataclasses for simple domain objects unless there is a clear reason not to.

Recommended default:

```python
from dataclasses import dataclass
```

Use frozen dataclasses where immutability is practical.

---

# Analysis Models

## MoveTransition

Represents a single move and its before/after board states.

Purpose:

The unit of analysis for detectors.

Expected file:

```text
src/ai_chess_coach/models/move_transition.py
```

Fields:

- `ply`
- `san`
- `move`
- `before_position`
- `after_position`

Notes:

- `ply` is the half-move number.
- `san` is the move in Standard Algebraic Notation.
- `move` should store the underlying python-chess move object or equivalent.
- `before_position` represents the board before the move.
- `after_position` represents the board after the move.

Do not store coaching explanations in this model.

---

## PositionAnalysis

Represents a board snapshot prepared for analysis.

Purpose:

Provides access to a board state and its associated `FeatureStore`.

Expected file:

```text
src/ai_chess_coach/models/position_analysis.py
```

Fields:

- `board`
- `fen`
- `feature_store`

Notes:

- `fen` should match the board position.
- `feature_store` should expose reusable chess facts for that position.
- This model should not perform detector logic directly.

---

## AttackerInfo

Represents a piece attacking a target square or piece.

Purpose:

Used by `PieceSafety` and tactical detectors.

Expected file:

```text
src/ai_chess_coach/models/piece_safety.py
```

Fields:

- `square`
- `piece`
- `is_pinned`

Notes:

- `square` is the attacker's square.
- `piece` is the attacking piece.
- `is_pinned` indicates whether the attacker is pinned.

---

## DefenderInfo

Represents a piece defending a target square or piece.

Purpose:

Used by `PieceSafety` and tactical detectors.

Expected file:

```text
src/ai_chess_coach/models/piece_safety.py
```

Fields:

- `square`
- `piece`
- `is_pinned`
- `is_overloaded`

Notes:

- `square` is the defender's square.
- `piece` is the defending piece.
- `is_pinned` indicates whether the defender is pinned.
- `is_overloaded` indicates whether the defender has multiple important defensive obligations.

---

## PieceSafety

Represents the tactical safety of a piece on an occupied square.

Purpose:

Shared tactical primitive used by many detectors.

Expected file:

```text
src/ai_chess_coach/models/piece_safety.py
```

Fields:

- `square`
- `piece`
- `attackers`
- `defenders`
- `is_pinned`
- `see_value`

Derived properties:

- `is_hanging`
- `is_loose`
- `is_under_defended`
- `is_outnumbered`

Rules:

- Empty squares should not have `PieceSafety` objects.
- Piece safety is about pieces, not empty squares.
- Pinned defenders may be unreliable.
- Pinned attackers may also require special handling.
- `see_value` may be optional in early tasks if SEE is not implemented yet.

Suggested meanings:

- `is_loose`: the piece has no defenders.
- `is_hanging`: the piece can be captured and has no reliable defense.
- `is_under_defended`: attackers are more dangerous than defenders.
- `is_outnumbered`: number of attackers is greater than number of defenders.

Exact implementation may evolve, but detectors must use this model rather than duplicating piece-safety logic.

---

## DetectedEvent

Represents a machine-facing chess occurrence found by a detector.

Purpose:

Raw detector output.

Expected file:

```text
src/ai_chess_coach/models/detected_event.py
```

Fields:

- `event_type`
- `side`
- `move`
- `position`
- `squares`
- `metadata`
- `evidence`
- `severity`
- `candidate_move`

`side` is the color/player the event is attributed to. It is not necessarily the
player who made the move. For `HangingPieceDetector`:

- `hanging_piece_created`: `side` is the color of the piece that became hanging.
- `hanging_piece_ignored`: `side` is the player who moved and ignored the opponent's hanging piece.
- `hanging_piece_lost`: `side` is the color of the hanging piece that was captured.

Examples of `event_type`:

- `hanging_piece_created`
- `hanging_piece_ignored`
- `hanging_piece_lost`
- `fork_created`
- `fork_missed`
- `fork_allowed`
- `knight_outpost_created`
- `knight_outpost_missed`

Rules:

- Must not contain coaching language.
- Must not contain LLM-generated explanations.
- Must be deterministic.
- Must be suitable for testing.

`candidate_move` is `None` for actual-move events. Counterfactual events such
as `fork_missed`, `fork_allowed`, and `knight_outpost_missed` use typed
candidate moves so engine verification can evaluate the candidate line without
reading move strings out of `evidence`.

---

## CandidateMove

Represents a typed candidate move attached to a counterfactual event.

Expected file:

```text
src/ai_chess_coach/models/candidate_move.py
```

Fields:

- `move_uci`
- `move_san`
- `start_fen`
- `side`

Rules:

- Used by engine verification.
- Does not replace detector-specific evidence used for display.
- Must not contain coaching language.

Good evidence:

```python
{
    "piece_square": "c4",
    "attackers": ["b5"],
    "defenders": []
}
```

Bad evidence:

```python
{
    "explanation": "You need to stop blundering bishops."
}
```

---

## EventTypeMetadata

Represents central metadata for detector event types.

Expected file:

```text
src/ai_chess_coach/models/event_type_metadata.py
```

Fields:

- `event_type`
- `display_name`
- `category`
- `polarity`
- `verification_kind`
- `is_execution_strength`

`verification_kind` describes how the engine layer should verify the event:

- `actual_move`: the played move caused the event.
- `missed_candidate`: the player had a candidate move but did not play it.
- `allowed_response`: the played move allowed an opponent candidate reply.

Unknown event types remain neutral and default to `actual_move` verification
metadata for deterministic backward compatibility.

`is_execution_strength` marks positive event types that can represent successful
execution evidence even when immediate engine impact is small. Current execution
strength event types are:

- `fork_created`
- `knight_outpost_created`

---

# Verification Models

## EngineScore

Represents one raw engine score from White's perspective.

Expected file:

```text
src/ai_chess_coach/models/engine_score.py
```

Fields:

- `centipawns`
- `mate`

Derived behavior:

- `kind`
- `rank_value()`
- `for_side(side)`

Exactly one of `centipawns` or `mate` may be set. If neither is set, the score
is unavailable.

`rank_value()` is an internal ordering value:

```text
centipawn score -> centipawns
mate > 0        -> 10_000_000 - abs(mate)
mate < 0        -> -10_000_000 + abs(mate)
mate == 0       -> 10_000_000
unavailable     -> None
```

Rank values are not centipawns and must not be presented as centipawn values in
user-facing text. They exist only to compare centipawn and mate outcomes
deterministically for verification, selection, and profile ordering.

---

## EngineAssessment

Represents objective engine evidence for a position or event.

Purpose:

Measures the importance of a detected event.

Expected file:

```text
src/ai_chess_coach/models/engine_assessment.py
```

Fields:

- `depth`
- `eval_before`
- `eval_after`
- `eval_delta`
- `eval_delta_for_event_side`
- `candidate_eval_after`
- `candidate_move_uci`
- `candidate_after_fen`
- `event_impact_for_side`
- `impact_magnitude`
- `score_before`
- `score_after`
- `candidate_score_after`
- `event_score_kind`
- `event_impact_rank_for_side`
- `impact_rank`
- `best_move`
- `principal_variation`

`eval_delta` remains the raw White-perspective delta for the actual played
move: `eval_after - eval_before`.

`eval_delta_for_event_side` is the actual played move delta from the attributed
event side's perspective. It is retained for debugging and compatibility.

`event_impact_for_side` is the canonical signed impact of the event for coaching
selection. Actual-move events usually use the actual played move impact. Missed
candidate and allowed-response events compare the actual position with the
candidate line represented by `CandidateMove`.

`impact_magnitude` is `abs(event_impact_for_side)` when available.

`event_score_kind` is:

- `centipawn` when the event comparison used only centipawn scores.
- `mate` when the event comparison involved at least one mate score.
- `unavailable` when required score data is missing.

`event_impact_rank_for_side` is the canonical mate-aware signed impact. Positive
means the event comparison improved the attributed side's position. Negative
means it worsened the attributed side's position. Zero means no rank change.
`impact_rank` is `abs(event_impact_rank_for_side)` when available.

Rank fields are internal ordering values. They are not centipawns and must not
be labeled or explained as centipawn values.

Rules:

- Created by the engine layer.
- Detectors must not create this directly by calling Stockfish.
- May represent centipawn or mate evaluations.

---

## VerifiedEvent

Combines a `DetectedEvent` with an `EngineAssessment`.

Purpose:

Trusted input for profiling and coaching.

Expected file:

```text
src/ai_chess_coach/models/verified_event.py
```

Fields:

- `event`
- `engine_assessment`

Rules:

- Verification must remain separate from detection.
- `VerifiedEvent` is allowed to be used by profiling, retrieval, and coaching layers.
- `VerifiedEvent` should not itself generate coaching language.
- Retrieval should order verified events by canonical verified impact:
  mate-aware `impact_rank` first, then centipawn/candidate-aware
  `impact_magnitude`, then detector `severity` as a fallback.
- Retrieval should not use raw `eval_delta` for event ordering because it is
  White-perspective actual-move evidence, not event-specific impact.

---

# Profiling Models

## DetectedPattern

Represents a recurring theme aggregated across verified events.

Purpose:

Turns isolated events into long-term player tendencies.

Expected file:

```text
src/ai_chess_coach/models/detected_pattern.py
```

Fields:

- `pattern_type`
- `frequency`
- `severity`
- `supporting_events`

Examples:

- `recurring_hanging_pieces`
- `recurring_missed_forks`
- `recurring_outpost_misuse`

Rules:

- Built from verified events.
- Should not be built directly from raw PGNs.
- Raw patterns from `PatternAggregator` may include every verified event of a
  type, including low-impact, neutral, or polarity-mismatched events.
- Profile-local patterns inside `WeaknessProfile` are rebuilt from
  coaching-relevant supporting events only.

---

## WeaknessProfile

Represents a player's long-term strengths and weaknesses.

Purpose:

Primary structured input for personalized coaching.

Expected file:

```text
src/ai_chess_coach/models/weakness_profile.py
```

Fields:

- `strengths`
- `execution_strengths`
- `weaknesses`
- `recurring_themes`

Rules:

- Built from detected patterns and verified events.
- User-facing fields contain profile-local `DetectedPattern` objects whose
  supporting events passed `CoachingRelevancePolicy`.
- Profile-local pattern severity is the average centipawn `impact_magnitude` for
  centipawn events or average mate-aware `impact_rank` for mate-scored events.
- `execution_strengths` contains profile-local `DetectedPattern` objects for
  non-contradicted positive execution evidence that did not meet the impact
  relevance threshold.
- Execution-strength pattern severity is an ordering score based on frequency,
  not centipawn or mate-rank impact.
- Neutral or unknown event types are excluded from user-facing profile fields.
- Raw `GameAnalysisResult.detected_patterns` remains the debugging source for
  unfiltered patterns.
- Must not be generated directly by an LLM.
- Must not be built directly from raw PGNs.

---

# Coaching Models

## CoachingMoment

Represents a user-facing lesson or explanation.

Purpose:

Human-facing teaching object derived from verified evidence.

Expected file:

```text
src/ai_chess_coach/models/coaching_moment.py
```

Fields:

- `title`
- `explanation`
- `supporting_evidence`
- `position_reference`
- `highlights`

Rules:

- May contain human-facing language.
- Must be grounded in verified events or detected patterns.
- Must not invent chess facts that are not present in evidence.

---

## LLMPrompt

Represents the provider-agnostic prompt boundary for future LLM clients.

Purpose:

Carries grounded coaching instructions and structured evidence without binding
the backend to a specific LLM provider.

Expected file:

```text
src/ai_chess_coach/coaching/llm_client.py
```

Fields:

- `system`
- `user`

Rules:

- Built by `PromptBuilder` from structured evidence only.
- Uses selected or retrieved evidence such as coaching moments, verified events,
  detected patterns, and weakness profiles.
- Must not accept raw PGNs as an evidence input.
- Must not ask the LLM to calculate moves, analyze positions, or verify tactics.
- Real provider clients and chat orchestration are outside the domain model.

---

# Model Lifecycle

The intended lifecycle is:

```text
MoveTransition
↓
PositionAnalysis
↓
FeatureStore
↓
DetectedEvent
↓
EngineAssessment
↓
VerifiedEvent
↓
DetectedPattern
↓
WeaknessProfile
↓
CoachingMoment
```

Do not bypass this lifecycle.

---

# Out Of Scope For Domain Models

Domain models should not handle:

- PGN parsing
- Stockfish process management
- LLM calls
- database persistence
- API serialization decisions beyond simple data representation
- frontend board rendering

Those responsibilities belong in other layers.
