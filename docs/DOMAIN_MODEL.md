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
- `evidence`
- `severity`

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

# Verification Models

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
- `best_move`
- `principal_variation`

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

- `patterns`
- `strengths`
- `weaknesses`
- `summary_stats`

Rules:

- Built from detected patterns and verified events.
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
