"""Attach engine evidence to detected events."""

from __future__ import annotations

from ai_chess_coach.engine.stockfish_engine import StockfishAnalysis, StockfishEngine
from ai_chess_coach.models import DetectedEvent, EngineAssessment, VerifiedEvent


class EventVerificationError(ValueError):
    """Raised when an event cannot be verified because its evidence is malformed."""


class EventVerifier:
    """Creates verified events by attaching engine evidence."""

    def __init__(self, engine: StockfishEngine) -> None:
        self.engine = engine

    def verify(self, event: DetectedEvent) -> VerifiedEvent:
        """Attach engine evidence to a detected event."""

        before_fen = _required_fen(event, "before_fen")
        after_fen = _required_fen(event, "after_fen")
        before_analysis = self.engine.evaluate_fen(before_fen)
        after_analysis = self.engine.evaluate_fen(after_fen)
        eval_before = _centipawn_score(before_analysis)
        eval_after = _centipawn_score(after_analysis)
        eval_delta = (
            eval_after - eval_before
            if eval_before is not None and eval_after is not None
            else None
        )

        return VerifiedEvent(
            event=event,
            engine_assessment=EngineAssessment(
                eval_before=eval_before,
                eval_after=eval_after,
                eval_delta=eval_delta,
                best_move=before_analysis.best_move,
                principal_variation=before_analysis.principal_variation,
                depth=before_analysis.depth,
            ),
        )


def _required_fen(event: DetectedEvent, key: str) -> str:
    value = event.evidence.get(key)
    if not isinstance(value, str):
        raise EventVerificationError(f"DetectedEvent evidence must include string {key!r}.")

    return value


def _centipawn_score(analysis: StockfishAnalysis) -> int | None:
    if analysis.score is None:
        return None

    return analysis.score.white().score()
