"""Detector for hanging-piece events."""

from __future__ import annotations

import chess

from ai_chess_coach.detectors.base import BaseDetector
from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import DetectedEvent, MoveTransition, PieceSafety

HANGING_PIECE_CREATED = "hanging_piece_created"
HANGING_PIECE_IGNORED = "hanging_piece_ignored"
HANGING_PIECE_LOST = "hanging_piece_lost"


class HangingPieceDetector(BaseDetector):
    """Detects hanging-piece events from one move transition."""

    def detect(self, transition: MoveTransition) -> list[DetectedEvent]:
        """Return hanging-piece events for a move transition."""

        before_hanging = _hanging_pieces(transition.before_position)
        after_hanging = _hanging_pieces(transition.after_position)
        mover = transition.before_position.turn
        events: list[DetectedEvent] = []

        for square in chess.SQUARES:
            safety = after_hanging.get(square)
            if safety is None:
                continue

            before_safety = before_hanging.get(square)
            if before_safety is not None and before_safety.piece == safety.piece:
                continue

            events.append(
                DetectedEvent(
                    event_type=HANGING_PIECE_CREATED,
                    side=safety.piece.color,
                    move=transition.move,
                    position=transition.after_position.copy(stack=False),
                    squares=(square,),
                    evidence=_event_evidence(safety, transition, before_hanging, after_hanging),
                    severity=1.0,
                )
            )

        for square in chess.SQUARES:
            safety = before_hanging.get(square)
            if safety is None or safety.piece.color == mover:
                continue

            after_safety = after_hanging.get(square)
            if after_safety is None or after_safety.piece != safety.piece:
                continue

            events.append(
                DetectedEvent(
                    event_type=HANGING_PIECE_IGNORED,
                    side=mover,
                    move=transition.move,
                    position=transition.before_position.copy(stack=False),
                    squares=(square,),
                    evidence=_event_evidence(safety, transition, before_hanging, after_hanging),
                    severity=1.0,
                )
            )

        captured_square = _captured_square(transition.before_position, transition.move)
        if captured_square is not None:
            safety = before_hanging.get(captured_square)
            if safety is not None:
                events.append(
                    DetectedEvent(
                        event_type=HANGING_PIECE_LOST,
                        side=safety.piece.color,
                        move=transition.move,
                        position=transition.before_position.copy(stack=False),
                        squares=(captured_square,),
                        evidence=_event_evidence(
                            safety,
                            transition,
                            before_hanging,
                            after_hanging,
                            captured_square=captured_square,
                            captured_piece=safety.piece,
                        ),
                        severity=1.0,
                    )
                )

        return events


def _hanging_pieces(board: chess.Board) -> dict[chess.Square, PieceSafety]:
    return {
        square: safety
        for square, safety in FeatureStore(board).piece_safety().items()
        if safety.is_hanging
    }


def _captured_square(board: chess.Board, move: chess.Move) -> chess.Square | None:
    if not board.is_capture(move):
        return None

    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)

    return move.to_square


def _event_evidence(
    safety: PieceSafety,
    transition: MoveTransition,
    before_hanging: dict[chess.Square, PieceSafety],
    after_hanging: dict[chess.Square, PieceSafety],
    *,
    captured_square: chess.Square | None = None,
    captured_piece: chess.Piece | None = None,
) -> dict[str, object]:
    evidence: dict[str, object] = {
        "piece_square": chess.square_name(safety.square),
        "piece": safety.piece.symbol(),
        "piece_color": _color_name(safety.piece.color),
        "attackers": tuple(chess.square_name(attacker.square) for attacker in safety.attackers),
        "defenders": tuple(chess.square_name(defender.square) for defender in safety.defenders),
        "before_hanging_squares": _square_names(before_hanging),
        "after_hanging_squares": _square_names(after_hanging),
        "move_uci": transition.move.uci(),
        "move_san": transition.san,
        "before_fen": transition.before_position.fen(),
        "after_fen": transition.after_position.fen(),
    }

    if captured_square is not None:
        evidence["captured_square"] = chess.square_name(captured_square)
    if captured_piece is not None:
        evidence["captured_piece"] = captured_piece.symbol()

    return evidence


def _square_names(piece_safety: dict[chess.Square, PieceSafety]) -> tuple[str, ...]:
    return tuple(chess.square_name(square) for square in chess.SQUARES if square in piece_safety)


def _color_name(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"
