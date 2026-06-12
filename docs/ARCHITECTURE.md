# System Architecture

## High Level Flow

PGN
→ Replay
→ MoveTransition
→ Feature Extraction
→ Detection
→ Engine Verification
→ Pattern Aggregation
→ Retrieval
→ AI Coach

## Layers

### Replay Layer

Responsible for reconstructing positions.

Input:
- PGN

Output:
- MoveTransition

### Feature Layer

Responsible for reusable board facts.

Examples:
- PieceSafety
- Mobility
- PinnedPieces
- PawnStructure

### Detector Layer

Responsible for identifying chess concepts.

Examples:
- HangingPieceDetector
- ForkDetector
- KnightOutpostDetector

Output:
- DetectedEvent

### Engine Layer

Responsible for objective validation.

Output:
- EngineAssessment
- VerifiedEvent

### Profiling Layer

Aggregates recurring weaknesses.

Output:
- DetectedPattern
- WeaknessProfile

### Coaching Layer

Generates human explanations.

Consumes:
- VerifiedEvents
- Patterns
- Examples
