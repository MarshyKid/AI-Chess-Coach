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
- Preserve mate scores as structured engine evidence.
- Verify candidate-aware event impact when an event represents a missed or allowed candidate move.
- Record best move and principal variation from the before-position analysis.

## Engine Scores And Rank Values

`EngineScore` stores either a centipawn score, a mate score, or unavailable
score data.

The internal rank formula is:

```text
centipawns      -> centipawns
mate > 0        -> 10_000_000 - abs(mate)
mate < 0        -> -10_000_000 + abs(mate)
mate == 0       -> 10_000_000
unavailable     -> None
```

Rank meaning:

- positive rank is good for the score perspective
- negative rank is bad for the score perspective
- favorable mate outranks all centipawn scores
- unfavorable mate ranks below all centipawn scores
- faster favorable mate ranks higher
- faster unfavorable mate ranks lower

Rank values are internal ordering values. They must never be described as
centipawns.

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
- Set `event_impact_rank_for_side = after_rank_for_side - before_rank_for_side`.

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
- Set `event_impact_rank_for_side = actual_after_rank_for_side - candidate_after_rank_for_side`.

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
- Set `event_impact_rank_for_side = candidate_after_rank_for_side - actual_after_rank_for_side`.

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
- `score_before`
- `score_after`
- `candidate_score_after`
- `event_score_kind`
- `event_impact_rank_for_side`
- `impact_rank`
- `best_move`
- `principal_variation`
- `depth`

`eval_delta` remains raw White-perspective actual-move evidence.

`event_impact_for_side` remains the canonical signed centipawn impact when the
comparison used only centipawn scores.

`event_impact_rank_for_side` is the canonical signed mate-aware impact. Positive
means the event comparison improved the attributed side's position. Negative
means it worsened that side's position. Zero means no rank change. `None` means
required score data is unavailable.

`event_score_kind` is `mate` when the event comparison involved at least one
mate score, including mixed centipawn-vs-mate comparisons. For mate comparisons,
centipawn impact fields may be `None`; rank fields carry the comparable impact.

## Rule

Only the engine layer may talk to Stockfish.
