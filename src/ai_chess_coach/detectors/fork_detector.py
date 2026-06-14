"""Detector for fork events."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from ai_chess_coach.detectors.base import BaseDetector
from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import DetectedEvent, EventMetadata, MoveTransition

FORK_CREATED = "fork_created"
FORK_MISSED = "fork_missed"
FORK_ALLOWED = "fork_allowed"

VALUABLE_TARGETS = {
    chess.KING,
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
}


@dataclass(frozen=True)
class ForkInfo:
    """Internal machine facts for one fork."""

    forking_square: chess.Square
    forking_piece: chess.Piece
    target_squares: tuple[chess.Square, ...]
    target_pieces: tuple[chess.Piece, ...]


class ForkDetector(BaseDetector):
    """Detects fork events from one move transition."""

    def detect(self, transition: MoveTransition) -> list[DetectedEvent]:
        """Return fork events for a move transition."""

        before_forks = _forks_in_position(transition.before_position)
        after_forks = _forks_in_position(transition.after_position)
        events: list[DetectedEvent] = []

        created_fork = after_forks.get(transition.move.to_square)
        if created_fork is not None and _is_new_actual_fork(
            before_forks, created_fork, transition.move
        ):
            events.append(
                DetectedEvent(
                    event_type=FORK_CREATED,
                    side=created_fork.forking_piece.color,
                    move=transition.move,
                    position=transition.after_position.copy(stack=False),
                    squares=(created_fork.forking_square,),
                    metadata=_event_metadata(transition),
                    evidence=_event_evidence(
                        created_fork,
                        transition,
                        transition.move,
                        transition.before_position,
                    ),
                    severity=1.0,
                )
            )

        legal_before_forks = _legal_fork_moves(transition.before_position)
        if transition.move not in legal_before_forks:
            for move, fork in sorted(legal_before_forks.items(), key=lambda item: item[0].uci()):
                events.append(
                    DetectedEvent(
                        event_type=FORK_MISSED,
                        side=transition.before_position.turn,
                        move=transition.move,
                        position=transition.before_position.copy(stack=False),
                        squares=(fork.forking_square,),
                        metadata=_event_metadata(transition),
                        evidence=_event_evidence(fork, transition, move, transition.before_position),
                        severity=1.0,
                    )
                )

        before_opponent_board = transition.before_position.copy(stack=False)
        before_opponent_board.turn = transition.after_position.turn
        legal_before_opponent_forks = _legal_fork_moves(before_opponent_board)
        legal_after_opponent_forks = _legal_fork_moves(transition.after_position)
        before_opportunity_keys = {
            _opportunity_key(move, fork) for move, fork in legal_before_opponent_forks.items()
        }

        for move, fork in sorted(legal_after_opponent_forks.items(), key=lambda item: item[0].uci()):
            if _opportunity_key(move, fork) in before_opportunity_keys:
                continue

            events.append(
                DetectedEvent(
                    event_type=FORK_ALLOWED,
                    side=transition.before_position.turn,
                    move=transition.move,
                    position=transition.after_position.copy(stack=False),
                    squares=(fork.forking_square,),
                    metadata=_event_metadata(transition),
                    evidence=_event_evidence(fork, transition, move, transition.after_position),
                    severity=1.0,
                )
            )

        return events


def _forks_in_position(board: chess.Board) -> dict[chess.Square, ForkInfo]:
    targets_by_attacker: dict[chess.Square, list[chess.Square]] = {}
    pieces_by_attacker: dict[chess.Square, chess.Piece] = {}

    for target_square, attackers in FeatureStore(board).attack_map().items():
        target_piece = board.piece_at(target_square)
        if target_piece is None or target_piece.piece_type not in VALUABLE_TARGETS:
            continue

        for attacker in attackers:
            if attacker.is_pinned:
                continue

            targets_by_attacker.setdefault(attacker.square, []).append(target_square)
            pieces_by_attacker[attacker.square] = attacker.piece

    forks: dict[chess.Square, ForkInfo] = {}
    for attacker_square in chess.SQUARES:
        target_squares = tuple(
            square for square in chess.SQUARES if square in targets_by_attacker.get(attacker_square, ())
        )
        if len(target_squares) < 2:
            continue

        target_pieces = tuple(
            piece
            for square in target_squares
            if (piece := board.piece_at(square)) is not None
        )
        forks[attacker_square] = ForkInfo(
            forking_square=attacker_square,
            forking_piece=pieces_by_attacker[attacker_square],
            target_squares=target_squares,
            target_pieces=target_pieces,
        )

    return forks


def _fork_created_by_move(board: chess.Board, move: chess.Move) -> ForkInfo | None:
    if move not in board.legal_moves:
        return None

    before_forks = _forks_in_position(board)
    after_board = board.copy(stack=False)
    after_board.push(move)
    fork = _forks_in_position(after_board).get(move.to_square)
    if fork is None:
        return None

    if not _is_new_actual_fork(before_forks, fork, move):
        return None

    return fork


def _legal_fork_moves(board: chess.Board) -> dict[chess.Move, ForkInfo]:
    fork_moves: dict[chess.Move, ForkInfo] = {}
    for move in sorted(board.legal_moves, key=lambda legal_move: legal_move.uci()):
        fork = _fork_created_by_move(board, move)
        if fork is not None:
            fork_moves[move] = fork

    return fork_moves


def _is_new_actual_fork(
    before_forks: dict[chess.Square, ForkInfo],
    fork: ForkInfo,
    move: chess.Move,
) -> bool:
    before_fork = before_forks.get(move.from_square)
    if before_fork is None or before_fork.forking_piece != fork.forking_piece:
        return True

    return before_fork.target_squares != fork.target_squares


def _event_evidence(
    fork: ForkInfo,
    transition: MoveTransition,
    forking_move: chess.Move,
    forking_position: chess.Board,
) -> dict[str, object]:
    return {
        "forking_piece_square": chess.square_name(fork.forking_square),
        "forking_piece": fork.forking_piece.symbol(),
        "forking_piece_color": _color_name(fork.forking_piece.color),
        "target_squares": tuple(chess.square_name(square) for square in fork.target_squares),
        "target_pieces": tuple(piece.symbol() for piece in fork.target_pieces),
        "forking_move_uci": forking_move.uci(),
        "forking_move_san": _san_for_move(forking_position, forking_move, transition),
    }


def _event_metadata(transition: MoveTransition) -> EventMetadata:
    return EventMetadata(
        before_fen=transition.before_position.fen(),
        after_fen=transition.after_position.fen(),
        move_uci=transition.move.uci(),
        move_san=transition.san,
        ply=transition.ply,
    )


def _san_for_move(
    board: chess.Board,
    move: chess.Move,
    transition: MoveTransition,
) -> str:
    if move == transition.move:
        return transition.san

    return board.san(move)


def _opportunity_key(move: chess.Move, fork: ForkInfo) -> tuple[str, tuple[chess.Square, ...]]:
    return (move.uci(), fork.target_squares)


def _color_name(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"
