"""Detector for knight outpost events."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from ai_chess_coach.detectors.base import BaseDetector
from ai_chess_coach.features import FeatureStore
from ai_chess_coach.models import (
    CandidateMove,
    DetectedEvent,
    EventMetadata,
    MoveTransition,
)

KNIGHT_OUTPOST_CREATED = "knight_outpost_created"
KNIGHT_OUTPOST_MISSED = "knight_outpost_missed"

CENTRAL_FILES = {2, 3, 4, 5}


@dataclass(frozen=True)
class OutpostInfo:
    """Internal machine facts for one knight outpost."""

    knight_square: chess.Square
    knight_piece: chess.Piece
    defending_pawn_squares: tuple[chess.Square, ...]
    enemy_pawn_attack_squares: tuple[chess.Square, ...]


class KnightOutpostDetector(BaseDetector):
    """Detects knight outpost events from one move transition."""

    def detect(self, transition: MoveTransition) -> list[DetectedEvent]:
        """Return knight outpost events for a move transition."""

        before_outposts = _outposts_in_position(transition.before_position)
        after_outposts = _outposts_in_position(transition.after_position)
        events: list[DetectedEvent] = []

        created_outpost = _outpost_created_by_move(
            transition.before_position,
            transition.move,
            before_outposts=before_outposts,
            after_outposts=after_outposts,
        )
        if created_outpost is not None:
            events.append(
                DetectedEvent(
                    event_type=KNIGHT_OUTPOST_CREATED,
                    side=created_outpost.knight_piece.color,
                    move=transition.move,
                    position=transition.after_position.copy(stack=False),
                    squares=(created_outpost.knight_square,),
                    metadata=_event_metadata(transition),
                    evidence=_event_evidence(
                        created_outpost,
                        transition,
                        transition.move,
                        transition.before_position,
                        before_outposts,
                        after_outposts,
                    ),
                    severity=1.0,
                )
            )

        legal_before_outposts = _legal_outpost_moves(transition.before_position)
        if transition.move not in legal_before_outposts:
            for move, outpost in sorted(
                legal_before_outposts.items(), key=lambda item: item[0].uci()
            ):
                events.append(
                    DetectedEvent(
                        event_type=KNIGHT_OUTPOST_MISSED,
                        side=transition.before_position.turn,
                        move=transition.move,
                        position=transition.before_position.copy(stack=False),
                        squares=(outpost.knight_square,),
                        metadata=_event_metadata(transition),
                        evidence=_event_evidence(
                            outpost,
                            transition,
                            move,
                            transition.before_position,
                            before_outposts,
                            after_outposts,
                        ),
                        severity=1.0,
                        candidate_move=_candidate_move(
                            move,
                            transition.before_position,
                            transition,
                        ),
                    )
                )

        return events


def _outposts_in_position(board: chess.Board) -> dict[chess.Square, OutpostInfo]:
    feature_store = FeatureStore(board)
    defender_map = feature_store.defender_map()
    attack_map = feature_store.attack_map()
    outposts: dict[chess.Square, OutpostInfo] = {}

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None or piece.piece_type != chess.KNIGHT:
            continue
        if not _is_advanced_outpost_square(square, piece.color):
            continue

        defending_pawn_squares = tuple(
            defender.square
            for defender in defender_map.get(square, ())
            if defender.piece.piece_type == chess.PAWN
        )
        enemy_pawn_attack_squares = tuple(
            attacker.square
            for attacker in attack_map.get(square, ())
            if attacker.piece.piece_type == chess.PAWN
        )
        if not defending_pawn_squares or enemy_pawn_attack_squares:
            continue

        outposts[square] = OutpostInfo(
            knight_square=square,
            knight_piece=piece,
            defending_pawn_squares=defending_pawn_squares,
            enemy_pawn_attack_squares=enemy_pawn_attack_squares,
        )

    return outposts


def _outpost_created_by_move(
    board: chess.Board,
    move: chess.Move,
    *,
    before_outposts: dict[chess.Square, OutpostInfo] | None = None,
    after_outposts: dict[chess.Square, OutpostInfo] | None = None,
) -> OutpostInfo | None:
    if move not in board.legal_moves:
        return None

    moved_piece = board.piece_at(move.from_square)
    if moved_piece is None or moved_piece.piece_type != chess.KNIGHT:
        return None

    if before_outposts is None:
        before_outposts = _outposts_in_position(board)
    if after_outposts is None:
        after_board = board.copy(stack=False)
        after_board.push(move)
        after_outposts = _outposts_in_position(after_board)

    outpost = after_outposts.get(move.to_square)
    if outpost is None or outpost.knight_piece != moved_piece:
        return None

    before_outpost = before_outposts.get(move.from_square)
    if before_outpost is not None and before_outpost.knight_piece == outpost.knight_piece:
        return None

    return outpost


def _legal_outpost_moves(board: chess.Board) -> dict[chess.Move, OutpostInfo]:
    outpost_moves: dict[chess.Move, OutpostInfo] = {}
    for move in sorted(board.legal_moves, key=lambda legal_move: legal_move.uci()):
        outpost = _outpost_created_by_move(board, move)
        if outpost is not None:
            outpost_moves[move] = outpost

    return outpost_moves


def _event_evidence(
    outpost: OutpostInfo,
    transition: MoveTransition,
    outpost_move: chess.Move,
    outpost_position: chess.Board,
    before_outposts: dict[chess.Square, OutpostInfo],
    after_outposts: dict[chess.Square, OutpostInfo],
) -> dict[str, object]:
    return {
        "knight_square": chess.square_name(outpost.knight_square),
        "knight_color": _color_name(outpost.knight_piece.color),
        "defending_pawn_squares": _square_names(outpost.defending_pawn_squares),
        "enemy_pawn_attack_squares": _square_names(outpost.enemy_pawn_attack_squares),
        "before_outpost_squares": _square_names(before_outposts),
        "after_outpost_squares": _square_names(after_outposts),
        "outpost_move_uci": outpost_move.uci(),
        "outpost_move_san": _san_for_move(outpost_position, outpost_move, transition),
    }


def _event_metadata(transition: MoveTransition) -> EventMetadata:
    return EventMetadata(
        before_fen=transition.before_position.fen(),
        after_fen=transition.after_position.fen(),
        move_uci=transition.move.uci(),
        move_san=transition.san,
        ply=transition.ply,
    )


def _candidate_move(
    move: chess.Move,
    board: chess.Board,
    transition: MoveTransition,
) -> CandidateMove:
    return CandidateMove(
        move_uci=move.uci(),
        move_san=_san_for_move(board, move, transition),
        start_fen=board.fen(),
        side=board.turn,
    )


def _is_advanced_outpost_square(square: chess.Square, color: chess.Color) -> bool:
    rank = chess.square_rank(square)
    file = chess.square_file(square)

    if color == chess.WHITE:
        return rank >= 4 or (rank == 3 and file in CENTRAL_FILES)

    return rank <= 3 or (rank == 4 and file in CENTRAL_FILES)


def _square_names(squares: tuple[chess.Square, ...] | dict[chess.Square, OutpostInfo]) -> tuple[str, ...]:
    if isinstance(squares, dict):
        return tuple(chess.square_name(square) for square in chess.SQUARES if square in squares)

    return tuple(chess.square_name(square) for square in squares)


def _san_for_move(
    board: chess.Board,
    move: chess.Move,
    transition: MoveTransition,
) -> str:
    if move == transition.move:
        return transition.san

    return board.san(move)


def _color_name(color: chess.Color) -> str:
    return "white" if color == chess.WHITE else "black"
