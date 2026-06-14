# Coaching Moment Selection

## Problem

The detector and verification layers can legitimately produce many `VerifiedEvent` objects for one game. A single move can create several detector findings, especially for tactical opportunity detectors like forks.

That raw volume is useful for debugging, pattern aggregation, and future drill generation, but it is too noisy for a user-facing review. A coach should not show every raw event as a separate lesson.

The intended distinction is:

```text
VerifiedEvent = raw verified evidence
CoachingMoment = selected teaching point
```

The system should keep all raw verified events, but generate only a small number of selected coaching moments.

## Principles

1. Detectors identify chess motifs. They do not decide what is worth coaching.
2. Engine verification measures objective impact. It should preserve raw engine evidence.
3. Coaching selection happens after verification, using verified evidence and event metadata.
4. The selector should reduce noise without deleting raw evidence from pipeline outputs.
5. The LLM coach should receive retrieved/selected evidence, not every raw event by default.

## Event Polarity

Event types need central metadata that describes their coaching meaning.

Examples:

```text
fork_created              -> positive
knight_outpost_created    -> positive
fork_missed               -> negative
fork_allowed              -> negative
hanging_piece_created     -> negative
hanging_piece_ignored     -> negative
hanging_piece_lost        -> negative
knight_outpost_missed     -> negative
```

This polarity should live in an event type metadata registry, not inside individual detectors and not as scattered hardcoded lists.

## Side-Aware Engine Impact

Raw Stockfish centipawn scores are stored from White's perspective. This is important objective evidence, but it is not enough for coaching selection.

For coaching, the system also needs impact from the attributed event side's perspective:

```text
if event.side is White:
    eval_delta_for_event_side = eval_delta
else:
    eval_delta_for_event_side = -eval_delta
```

Interpretation:

```text
positive side-aware delta -> better for the attributed side
negative side-aware delta -> worse for the attributed side
```

This prevents a positive-looking motif from being celebrated when the move was actually bad for the player who created it.

Example:

```text
fork_created by White, eval_delta_for_event_side = +180
```

This can be a good coaching moment.

```text
fork_created by White, eval_delta_for_event_side = -300
```

This should not be promoted as a strength. The motif may exist, but the move was bad overall.

## Selection Rules

A first version of coaching selection should be deterministic and simple.

Recommended default rules:

1. Compute side-aware impact for each verified event.
2. Look up event type polarity.
3. Filter out events with no meaningful engine impact.
4. Filter out low-impact events below a threshold such as 80 centipawns.
5. Filter out polarity-mismatched events:
   * positive event type but bad for event side
   * negative event type but not meaningfully bad for event side
6. Group related same-move events when they represent one underlying lesson.
7. Rank candidates by impact magnitude.
8. Limit the review to a small number of moments, such as top 5.

## Grouping

Grouping should reduce repeated lessons without hiding evidence.

A useful first grouping key is:

```text
metadata.ply + event.side + event category + event polarity
```

This means multiple fork misses from the same move can become one coaching moment with several supporting events.

The `CoachingMoment.supporting_evidence` tuple should preserve the grouped `VerifiedEvent` objects.

Good grouping:

```text
Move 16: multiple fork opportunities missed
supporting evidence:
- fork_missed on e6
- fork_missed on e8
- fork_missed on f6
```

Bad grouping:

```text
Move 16: fork created and queen hung
```

Positive and negative events should not be merged into a single celebratory moment without careful explanation.

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

* debugging
* pattern aggregation
* drill generation
* detailed evidence retrieval
* LLM grounding

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
