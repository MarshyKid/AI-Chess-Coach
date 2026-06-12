# Detector Framework

## Goal

Detectors identify chess concepts.

They do NOT:

- explain
- coach
- use LLMs

They ONLY identify events.

## Interface

class BaseDetector:

    def detect(
        self,
        transition: MoveTransition
    ) -> list[DetectedEvent]

## Detector Lifecycle

MoveTransition
    ↓
FeatureStore
    ↓
Detector
    ↓
DetectedEvent

## Rules

Detectors must:

- be deterministic
- be unit-testable
- use FeatureStore
- avoid duplicated logic

## Initial Detectors

1. HangingPieceDetector
2. ForkDetector
3. KnightOutpostDetector
