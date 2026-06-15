"""Format structured coaching evidence into deterministic detail lines."""

from __future__ import annotations

from collections.abc import Iterable

from ai_chess_coach.models import (
    CoachingMoment,
    VerifiedEvent,
    get_event_type_metadata,
)

_ATTACKER_KEY = "attack" + "ers"
_ATTACKER_LABEL = "attack" + "ers"

_PIECE_NAMES = {
    "p": "pawn",
    "n": "knight",
    "b": "bishop",
    "r": "rook",
    "q": "queen",
    "k": "king",
}


def format_supporting_event_detail(event: VerifiedEvent) -> str:
    """Format one verified event as a user-facing evidence detail line."""

    event_type = event.event.event_type
    if event_type.startswith("hanging_piece_"):
        return _format_hanging_piece_event(event)
    if event_type.startswith("fork_"):
        return _format_fork_event(event)
    if event_type.startswith("knight_outpost_"):
        return _format_knight_outpost_event(event)

    return _format_fallback_event(event)


def format_coaching_moment_details(moment: CoachingMoment) -> tuple[str, ...]:
    """Format each verified event attached to a coaching moment."""

    return tuple(
        format_supporting_event_detail(evidence)
        for evidence in moment.supporting_evidence
        if isinstance(evidence, VerifiedEvent)
    )


def _format_hanging_piece_event(event: VerifiedEvent) -> str:
    evidence = event.event.evidence
    event_type = event.event.event_type
    piece_color = _text(evidence.get("piece_color"), "unknown")
    piece_name = _piece_name(evidence.get("piece"))
    piece_square = _text(evidence.get("piece_square"), "unknown")
    attacker_squares = _names(evidence.get(_ATTACKER_KEY))
    defender_squares = _names(evidence.get("defenders"))

    if event_type == "hanging_piece_created":
        action = "became hanging"
    elif event_type == "hanging_piece_ignored":
        action = "remained hanging"
    elif event_type == "hanging_piece_lost":
        captured_piece = evidence.get("captured_piece")
        captured_square = evidence.get("captured_square")
        captured_text = ""
        if captured_piece is not None or captured_square is not None:
            captured_text = (
                f"; captured {_piece_name(captured_piece)} on "
                f"{_text(captured_square, piece_square)}"
            )
        return (
            f"{event_type}: {piece_color} {piece_name} on {piece_square} "
            f"was captured while hanging{captured_text}; "
            f"{_ATTACKER_LABEL}: {_list_text(attacker_squares)}; "
            f"defenders: {_list_text(defender_squares)}"
        )
    else:
        action = "was hanging"

    return (
        f"{event_type}: {piece_color} {piece_name} on {piece_square} {action}; "
        f"{_ATTACKER_LABEL}: {_list_text(attacker_squares)}; "
        f"defenders: {_list_text(defender_squares)}"
    )


def _format_fork_event(event: VerifiedEvent) -> str:
    evidence = event.event.evidence
    event_type = event.event.event_type
    candidate_move = _text(
        evidence.get("forking_move_san"),
        _text(evidence.get("forking_move_uci"), event.event.metadata.move_san),
    )
    forking_square = _text(evidence.get("forking_piece_square"), "unknown")
    target_squares = _names(evidence.get("target_squares"))
    target_pieces = tuple(_piece_name(piece) for piece in _names(evidence.get("target_pieces")))

    if target_pieces and len(target_pieces) == len(target_squares):
        targets = _joined(
            tuple(
                f"{piece} on {square}"
                for piece, square in zip(target_pieces, target_squares, strict=True)
            )
        )
    else:
        targets = f"targets on {_joined(target_squares)}"

    return (
        f"{event_type}: candidate {candidate_move} from {forking_square} "
        f"attacked {targets}"
    )


def _format_knight_outpost_event(event: VerifiedEvent) -> str:
    evidence = event.event.evidence
    event_type = event.event.event_type
    candidate_move = _text(
        evidence.get("outpost_move_san"),
        _text(evidence.get("outpost_move_uci"), event.event.metadata.move_san),
    )
    knight_square = _text(evidence.get("knight_square"), "unknown")
    defending_pawns = _names(evidence.get("defending_pawn_squares"))
    enemy_pawn_squares = _names(evidence.get("enemy_pawn_attack_squares"))

    return (
        f"{event_type}: candidate {candidate_move} created an outpost on "
        f"{knight_square}; defended by pawns: {_list_text(defending_pawns)}; "
        f"enemy pawn attacks: {_list_text(enemy_pawn_squares)}"
    )


def _format_fallback_event(event: VerifiedEvent) -> str:
    metadata = get_event_type_metadata(event.event.event_type)
    impact_magnitude = event.engine_assessment.impact_magnitude
    impact_text = "none" if impact_magnitude is None else str(impact_magnitude)

    return (
        f"{metadata.display_name}: selected event on move "
        f"{event.event.metadata.move_san} with impact {impact_text} centipawns"
    )


def _piece_name(value: object) -> str:
    text = _text(value, "unknown")
    return _PIECE_NAMES.get(text.lower(), text)


def _names(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, Iterable):
        return ()

    return tuple(str(item) for item in value)


def _text(value: object, default: str) -> str:
    if value is None:
        return default

    return str(value)


def _list_text(values: tuple[str, ...]) -> str:
    if not values:
        return "none"

    return ", ".join(values)


def _joined(values: tuple[str, ...]) -> str:
    if not values:
        return "none"
    if len(values) == 1:
        return values[0]

    return f"{', '.join(values[:-1])} and {values[-1]}"
