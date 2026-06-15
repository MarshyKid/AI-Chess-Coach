# Engine Verification

Purpose:

Validate detector findings with objective engine evidence.

Detector answers:

"What happened?"

Engine answers:

"How important was it?"

## Responsibilities

- Run Stockfish through the engine layer only.
- Compute raw actual-move evaluation changes.
- Verify candidate-aware event impact when an event represents a missed or allowed candidate move.
- Record best move and principal variation from the before-position analysis.

## Verification Kinds

Event verification is driven by `EventTypeMetadata.verification_kind`.

### actual_move

Used when the played move itself caused the event.

Examples:

- `hanging_piece_created`
- `hanging_piece_ignored`
- `hanging_piece_lost`
- `fork_created`
- `knight_outpost_created`

Verification:

- Evaluate `before_fen`.
- Evaluate `after_fen`.
- Keep `eval_delta = eval_after - eval_before` from White's perspective.
- Set `event_impact_for_side` to the actual-move delta from the attributed event side's perspective.

### missed_candidate

Used when the player had a candidate move but did not play it.

Examples:

- `fork_missed`
- `knight_outpost_missed`

Verification:

- Evaluate `before_fen`.
- Evaluate the actual `after_fen`.
- Push `DetectedEvent.candidate_move` from `candidate_move.start_fen`.
- Evaluate the candidate-after FEN.
- Set `event_impact_for_side` to actual-after minus candidate-after from the attributed event side's perspective.

Negative impact means missing the candidate hurt the attributed side.

### allowed_response

Used when the played move allowed an opponent candidate reply.

Example:

- `fork_allowed`

Verification:

- Evaluate `before_fen`.
- Evaluate the actual `after_fen`.
- Push `DetectedEvent.candidate_move` from the actual after-position.
- Evaluate the candidate-after FEN.
- Set `event_impact_for_side` to candidate-after minus actual-after from the attributed event side's perspective.

Negative impact means the opponent reply would hurt the side who allowed it.

## Output

`EngineAssessment`

Important fields:

- `eval_before`
- `eval_after`
- `eval_delta`
- `eval_delta_for_event_side`
- `candidate_eval_after`
- `candidate_move_uci`
- `candidate_after_fen`
- `event_impact_for_side`
- `impact_magnitude`
- `best_move`
- `principal_variation`
- `depth`

`eval_delta` remains raw White-perspective actual-move evidence. `event_impact_for_side` is the canonical signed impact for coaching selection.

## Rule

Only the engine layer may talk to Stockfish.
