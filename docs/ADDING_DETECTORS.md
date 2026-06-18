# Adding Detectors

This guide explains how to add future detectors without breaking the AI Chess Coach architecture.

Read this before adding any new detector.

## Current Roadmap Priority

Detector expansion is intentionally postponed until after the product-facing
vertical slice in `docs/TASKS_31_40.md`.

The current detector set is sufficient for the MVP demo:

- `HangingPieceDetector`
- `ForkDetector`
- `KnightOutpostDetector`

The next priority is:

```text
PGN input -> backend analysis -> selected coaching evidence -> real LLM answer -> simple UI
```

Do not start a new detector task until the real provider, backend LLM CLI,
minimal API, minimal frontend, board viewer, and product polish tasks are
complete or explicitly reprioritized. Once detector work resumes, the process in
this guide remains the required process.

## Core Rule

Detectors identify structured chess events. They do not decide coaching value and they do not explain chess to the user.

The full pipeline is:

```text
PGN → Replay → MoveTransition → FeatureStore → Detector → DetectedEvent → EngineAssessment → VerifiedEvent → PatternAggregation → WeaknessProfile → Retrieval/Coaching → LLM explains evidence only
```

Detectors live only in this part:

```text
MoveTransition → FeatureStore → Detector → DetectedEvent
```

## Detector Responsibilities

A detector should answer:

```text
What chess motif or event exists in this move transition?
```

A detector may:

- inspect `MoveTransition.before_position`
- inspect `MoveTransition.after_position`
- use `FeatureStore`
- use python-chess board and move APIs for deterministic detection
- emit `DetectedEvent` objects
- attach structured machine-readable `evidence`
- attach `CandidateMove` for counterfactual events

A detector must not:

- call Stockfish
- import `ai_chess_coach.engine`
- call LLMs
- import OpenAI or other LLM clients
- generate coaching prose
- decide whether an event is worth showing to the user
- build `VerifiedEvent`
- build `EngineAssessment`
- build `CoachingMoment`
- perform persistence, API, auth, deployment, or frontend work

## One Detector At A Time

Add one detector per task.

Do not combine unrelated detector work. For example, do not add `PinDetector`, `SkewerDetector`, and pawn structure foundations in the same task.

A good detector task should include:

- one detector
- event type metadata
- detector tests
- verifier tests if candidate moves are introduced
- selector/review tests only if output behavior changes
- docs updates

## Step 1 — Define Event Types

Before coding the detector, define the event types it can emit.

Event type names should be:

- lowercase
- snake_case
- deterministic
- specific enough to classify later
- free of coaching language

Good examples:

```text
pin_created
pin_missed
pin_allowed
loose_piece_created
back_rank_weakness_allowed
passed_pawn_created
```

Bad examples:

```text
you_blundered_a_pin
should_have_seen_tactic
bad_move
nice_trick
```

## Step 2 — Classify Each Event Type

Every event type should be registered in `src/ai_chess_coach/models/event_type_metadata.py`.

For each event type, define:

- `event_type`
- `display_name`
- `category`
- `polarity`
- `verification_kind`

Example:

```python
EventTypeMetadata(
    event_type="pin_missed",
    display_name="Pin Missed",
    category="tactics",
    polarity="negative",
    verification_kind="missed_candidate",
)
```

## Event Polarity

Use polarity to describe how the event should be interpreted by downstream coaching selection.

```text
positive -> good for the attributed side when engine impact confirms it
negative -> bad for the attributed side when engine impact confirms it
neutral  -> not promoted by default
```

Examples:

```text
fork_created              -> positive
knight_outpost_created    -> positive
hanging_piece_created     -> negative
fork_missed               -> negative
fork_allowed              -> negative
```

Do not hardcode polarity in selectors or profile builders when the registry can provide it.

## Verification Kinds

The verifier uses `EventTypeMetadata.verification_kind` to decide how to compute `event_impact_for_side`.

### actual_move

Use this when the played move itself caused the event.

Examples:

```text
hanging_piece_created
fork_created
knight_outpost_created
```

Candidate move:

```text
None
```

Verification compares:

```text
before_fen → after_fen
```

### missed_candidate

Use this when the player had a candidate move but did not play it.

Examples:

```text
fork_missed
knight_outpost_missed
pin_missed
```

Candidate move:

```text
CandidateMove.start_fen = transition.before_position.fen()
CandidateMove.side = transition.before_position.turn
```

Verification compares:

```text
actual after-position vs candidate after-position from before_fen
```

For negative missed-candidate events, selection expects:

```text
event_impact_for_side < 0
```

### allowed_response

Use this when the played move allowed the opponent a candidate reply.

Examples:

```text
fork_allowed
pin_allowed
skewer_allowed
back_rank_weakness_allowed
```

Candidate move:

```text
CandidateMove.start_fen = transition.after_position.fen()
CandidateMove.side = transition.after_position.turn
```

Verification compares:

```text
actual after-position vs opponent candidate after-position
```

For negative allowed-response events, selection expects:

```text
event_impact_for_side < 0
```

## Step 3 — Decide The Attributed Side

`DetectedEvent.side` is the side the event is attributed to.

It is not always the side who makes the candidate move.

Examples:

```text
fork_created:
    side = color of the piece creating the fork

fork_missed:
    side = player who could have played the candidate fork

fork_allowed:
    side = player who made the move that allowed the opponent fork
```

For `allowed_response` events, `event.side` is usually the player who allowed the tactic, while `candidate_move.side` is the opponent.

## Step 4 — Populate EventMetadata

Every `DetectedEvent` should include `EventMetadata`:

```python
EventMetadata(
    before_fen=transition.before_position.fen(),
    after_fen=transition.after_position.fen(),
    move_uci=transition.move.uci(),
    move_san=transition.san,
    ply=transition.ply,
)
```

Do not hide FENs inside `evidence` if they belong in metadata.

## Step 5 — Populate CandidateMove When Needed

Use `CandidateMove` only when the event is counterfactual.

Required fields:

```python
CandidateMove(
    move_uci=move.uci(),
    move_san=board.san(move),
    start_fen=board.fen(),
    side=board.turn,
)
```

Rules:

- `actual_move` events usually use `candidate_move=None`.
- `missed_candidate` events start from the before-position.
- `allowed_response` events start from the after-position.
- The verifier will validate candidate start FEN, side, UCI, and legality.
- Keep existing display evidence separately from `CandidateMove`.

## Step 6 — Populate Structured Evidence

`DetectedEvent.evidence` should contain deterministic machine facts that are useful for tests, formatting, retrieval, and later LLM explanation.

Good evidence:

```python
{
    "forking_piece_square": "e6",
    "forking_piece": "Q",
    "target_squares": ("c6", "e7"),
    "target_pieces": ("n", "b"),
    "forking_move_uci": "f7e6",
    "forking_move_san": "Qe6",
}
```

Bad evidence:

```python
{
    "advice": "You should have played Qe6 because it wins material.",
    "explanation": "This was a bad mistake.",
}
```

Evidence should describe what the detector found, not whether the event deserves coaching. Engine verification and coaching selection decide that later.

## Step 7 — Use FeatureStore When Possible

Use `FeatureStore` for reusable chess facts such as:

- attack maps
- defender maps
- piece safety
- pinned pieces
- future reusable board features

Do not duplicate feature calculations inside detectors if the logic belongs in `FeatureStore`.

If a detector needs a new reusable feature, consider adding it to `FeatureStore` in a separate focused task before building the detector.

## Step 8 — Keep Detector Output Deterministic

Detector output order should be stable.

Recommended patterns:

- iterate over `chess.SQUARES` when scanning board squares
- sort legal moves by `move.uci()` before evaluating candidate moves
- sort event output when natural iteration order may vary
- use tuples rather than mutable lists inside evidence where practical

Stable output makes tests and future golden PGN regression tests reliable.

## Step 9 — Add Tests

A detector task should usually include the following tests.

### Detector tests

Test that the detector:

- emits the expected event type
- sets the correct `side`
- sets correct `metadata`
- sets stable `squares`
- sets structured `evidence`
- sets `candidate_move` when needed
- leaves `candidate_move=None` for actual-move events
- does not emit obvious false positives

### Event metadata tests

Test that new event types are registered with correct:

- display name
- category
- polarity
- verification kind

### Verifier tests

Required when the detector emits counterfactual events.

Test that:

- missed-candidate events evaluate candidate moves from `before_fen`
- allowed-response events evaluate candidate replies from `after_fen`
- wrong-side, illegal, invalid, or mismatched candidate moves are handled deterministically
- Black-side events flip perspective correctly

### Selector/review tests

Only update selector or review tests when selection or output expectations change.

The selector should remain chess-agnostic and should use:

```text
event_impact_for_side
impact_magnitude
event polarity
```

### Static architecture tests

Keep or add tests proving detectors do not import:

```text
ai_chess_coach.engine
stockfish
openai
llm clients
coaching prose layers
```

## Step 10 — Update Docs

A detector task should update docs only where the behavior changes.

Usually relevant docs:

- `docs/ADDING_DETECTORS.md`
- `docs/DETECTOR_FRAMEWORK.md`
- `docs/DOMAIN_MODEL.md`
- `docs/ENGINE_VERIFICATION.md`
- `docs/COACHING_SELECTION.md`
- task roadmap docs

Do not add frontend, API, database, auth, persistence, deployment, or LLM docs as part of a detector-only task.

## Detector Implementation Checklist

Use this checklist before marking a detector task complete.

```text
[ ] One detector only
[ ] Event types named and documented
[ ] EventTypeMetadata updated
[ ] Polarity chosen centrally
[ ] VerificationKind chosen centrally
[ ] DetectedEvent.side is correct
[ ] EventMetadata is populated
[ ] CandidateMove is populated for missed/allowed events
[ ] Evidence contains structured facts only
[ ] No coaching prose in detectors
[ ] No Stockfish or engine imports in detectors
[ ] No LLM imports or calls in detectors
[ ] Uses FeatureStore when appropriate
[ ] Output order is deterministic
[ ] Detector tests added or updated
[ ] Verifier tests added if candidate_move is used
[ ] Selector/review tests updated only if needed
[ ] Docs updated only where relevant
[ ] uv run python -m unittest discover -s tests passes
```

## Example Skeleton

```python
from __future__ import annotations

import chess

from ai_chess_coach.detectors.base import BaseDetector
from ai_chess_coach.models import CandidateMove, DetectedEvent, EventMetadata, MoveTransition


class ExampleDetector(BaseDetector):
    """Detects one deterministic chess motif."""

    def detect(self, transition: MoveTransition) -> list[DetectedEvent]:
        events: list[DetectedEvent] = []

        # Use FeatureStore or python-chess to find structured events.
        # Do not call Stockfish.
        # Do not generate coaching text.

        return events


def _event_metadata(transition: MoveTransition) -> EventMetadata:
    return EventMetadata(
        before_fen=transition.before_position.fen(),
        after_fen=transition.after_position.fen(),
        move_uci=transition.move.uci(),
        move_san=transition.san,
        ply=transition.ply,
    )


def _candidate_move(move: chess.Move, board: chess.Board) -> CandidateMove:
    return CandidateMove(
        move_uci=move.uci(),
        move_san=board.san(move),
        start_fen=board.fen(),
        side=board.turn,
    )
```

## Common Mistakes

Avoid these:

- using Stockfish inside a detector
- filtering detector events by engine impact inside a detector
- storing candidate moves only as strings in `evidence`
- omitting `CandidateMove` for missed or allowed events
- using `eval_delta` directly for coaching selection
- assigning `side` to the candidate mover for `allowed_response` events instead of the side who allowed the tactic
- putting user-facing advice in evidence
- adding several detectors in one task
- changing frontend/API/database/auth/deployment in a detector task
