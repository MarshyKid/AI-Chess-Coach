# Domain Model

## MoveTransition

Represents a move.

Fields:

- ply
- san
- move
- before_position
- after_position

## PositionAnalysis

Represents a board snapshot.

Fields:

- board
- fen
- feature_store

## PieceSafety

Represents tactical safety.

Fields:

- square
- piece
- attackers
- defenders
- is_pinned
- see_value

Derived:

- is_hanging
- is_loose
- is_under_defended
- is_outnumbered

## AttackerInfo

Fields:

- square
- piece
- is_pinned

## DefenderInfo

Fields:

- square
- piece
- is_pinned
- is_overloaded

## DetectedEvent

Fields:

- event_type
- side
- move
- position
- evidence
- severity

## EngineAssessment

Fields:

- depth
- eval_before
- eval_after
- eval_delta
- best_move
- principal_variation

## VerifiedEvent

Fields:

- event
- engine_assessment

## DetectedPattern

Fields:

- pattern_type
- frequency
- severity
- supporting_events

## WeaknessProfile

Fields:

- patterns
- strengths
- weaknesses
