"""Attach engine evidence to detected events."""

from __future__ import annotations

import chess

from ai_chess_coach.engine.stockfish_engine import StockfishAnalysis, StockfishEngine
from ai_chess_coach.models import (
    CandidateMove,
    DetectedEvent,
    EngineAssessment,
    VerifiedEvent,
    get_event_type_metadata,
)


class EventVerificationError(ValueError):
    """Raised when an event cannot be verified because its input is invalid."""


class EventVerifier:
    """Creates verified events by attaching engine evidence."""

    def __init__(self, engine: StockfishEngine) -> None:
        self.engine = engine

    def verify(self, event: DetectedEvent) -> VerifiedEvent:
        """Attach engine evidence to a detected event."""

        before_fen = event.metadata.before_fen
        after_fen = event.metadata.after_fen
        before_analysis = self.engine.evaluate_fen(before_fen)
        after_analysis = self.engine.evaluate_fen(after_fen)
        eval_before = _centipawn_score(before_analysis)
        eval_after = _centipawn_score(after_analysis)
        eval_delta = _delta(eval_before, eval_after)
        eval_delta_for_event_side = _side_aware_delta(eval_delta, event.side)
        event_type_metadata = get_event_type_metadata(event.event_type)
        candidate_eval_after: int | None = None
        candidate_move_uci: str | None = None
        candidate_after_fen: str | None = None

        if event_type_metadata.verification_kind == "actual_move":
            event_impact_for_side = eval_delta_for_event_side
        elif event_type_metadata.verification_kind == "missed_candidate":
            candidate_after_fen, candidate_move_uci = _candidate_after_fen(
                event.candidate_move,
                expected_start_fen=before_fen,
            )
            candidate_eval_after = _centipawn_score(
                self.engine.evaluate_fen(candidate_after_fen)
            )
            event_impact_for_side = _missed_candidate_impact(
                eval_after,
                candidate_eval_after,
                event.side,
            )
        elif event_type_metadata.verification_kind == "allowed_response":
            candidate_after_fen, candidate_move_uci = _candidate_after_fen(
                event.candidate_move,
                expected_start_fen=after_fen,
            )
            candidate_eval_after = _centipawn_score(
                self.engine.evaluate_fen(candidate_after_fen)
            )
            event_impact_for_side = _allowed_response_impact(
                eval_after,
                candidate_eval_after,
                event.side,
            )
        else:
            raise EventVerificationError(
                f"Unsupported verification kind: {event_type_metadata.verification_kind}"
            )

        impact_magnitude = (
            abs(event_impact_for_side)
            if event_impact_for_side is not None
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
                eval_delta_for_event_side=eval_delta_for_event_side,
                impact_magnitude=impact_magnitude,
                candidate_eval_after=candidate_eval_after,
                candidate_move_uci=candidate_move_uci,
                candidate_after_fen=candidate_after_fen,
                event_impact_for_side=event_impact_for_side,
            ),
        )


def _centipawn_score(analysis: StockfishAnalysis) -> int | None:
    if analysis.score is None:
        return None

    return analysis.score.white().score()


def _delta(before: int | None, after: int | None) -> int | None:
    if before is None or after is None:
        return None

    return after - before


def _side_aware_delta(eval_delta: int | None, side: chess.Color) -> int | None:
    if eval_delta is None:
        return None

    return eval_delta if side == chess.WHITE else -eval_delta


def _score_for_side(eval_score: int | None, side: chess.Color) -> int | None:
    if eval_score is None:
        return None

    return eval_score if side == chess.WHITE else -eval_score


def _missed_candidate_impact(
    actual_eval_after: int | None,
    candidate_eval_after: int | None,
    side: chess.Color,
) -> int | None:
    actual_for_side = _score_for_side(actual_eval_after, side)
    candidate_for_side = _score_for_side(candidate_eval_after, side)
    if actual_for_side is None or candidate_for_side is None:
        return None

    return actual_for_side - candidate_for_side


def _allowed_response_impact(
    actual_eval_after: int | None,
    candidate_eval_after: int | None,
    side: chess.Color,
) -> int | None:
    actual_for_side = _score_for_side(actual_eval_after, side)
    candidate_for_side = _score_for_side(candidate_eval_after, side)
    if actual_for_side is None or candidate_for_side is None:
        return None

    return candidate_for_side - actual_for_side


def _candidate_after_fen(
    candidate_move: CandidateMove | None,
    *,
    expected_start_fen: str,
) -> tuple[str, str]:
    if candidate_move is None:
        raise EventVerificationError("Candidate move is required for this event type.")
    if candidate_move.start_fen != expected_start_fen:
        raise EventVerificationError("Candidate move start FEN does not match event context.")

    try:
        board = chess.Board(candidate_move.start_fen)
    except ValueError as exc:
        raise EventVerificationError("Candidate move start FEN is invalid.") from exc

    if board.turn != candidate_move.side:
        raise EventVerificationError("Candidate move side does not match start position.")

    try:
        move = chess.Move.from_uci(candidate_move.move_uci)
    except ValueError as exc:
        raise EventVerificationError("Candidate move UCI is invalid.") from exc

    if move not in board.legal_moves:
        raise EventVerificationError("Candidate move is not legal in start position.")

    board.push(move)
    return board.fen(), move.uci()
