import unittest

import chess

from ai_chess_coach.models import AttackerInfo, DefenderInfo, PieceSafety


def attacker(
    square: chess.Square = chess.E4,
    piece: chess.Piece | None = None,
    is_pinned: bool = False,
) -> AttackerInfo:
    return AttackerInfo(
        square=square,
        piece=piece or chess.Piece(chess.KNIGHT, chess.BLACK),
        is_pinned=is_pinned,
    )


def defender(
    square: chess.Square = chess.F3,
    piece: chess.Piece | None = None,
    is_pinned: bool = False,
    is_overloaded: bool = False,
) -> DefenderInfo:
    return DefenderInfo(
        square=square,
        piece=piece or chess.Piece(chess.KNIGHT, chess.WHITE),
        is_pinned=is_pinned,
        is_overloaded=is_overloaded,
    )


def piece_safety(
    attackers: tuple[AttackerInfo, ...] = (),
    defenders: tuple[DefenderInfo, ...] = (),
    is_pinned: bool = False,
) -> PieceSafety:
    return PieceSafety(
        square=chess.D4,
        piece=chess.Piece(chess.BISHOP, chess.WHITE),
        attackers=attackers,
        defenders=defenders,
        is_pinned=is_pinned,
    )


class PieceSafetyTest(unittest.TestCase):
    def test_loose_when_piece_has_no_defenders(self) -> None:
        safety = piece_safety()

        self.assertTrue(safety.is_loose)

    def test_not_loose_when_piece_has_any_defender(self) -> None:
        safety = piece_safety(defenders=(defender(is_pinned=True),))

        self.assertFalse(safety.is_loose)

    def test_hanging_when_attacked_and_without_reliable_defenders(self) -> None:
        safety = piece_safety(attackers=(attacker(),))

        self.assertTrue(safety.is_hanging)

    def test_not_hanging_when_unattacked_even_if_loose(self) -> None:
        safety = piece_safety()

        self.assertFalse(safety.is_hanging)

    def test_not_hanging_when_reliably_defended(self) -> None:
        safety = piece_safety(
            attackers=(attacker(),),
            defenders=(defender(),),
        )

        self.assertFalse(safety.is_hanging)

    def test_pinned_or_overloaded_defenders_are_not_reliable(self) -> None:
        safety = piece_safety(
            attackers=(attacker(),),
            defenders=(
                defender(square=chess.F3, is_pinned=True),
                defender(square=chess.E2, is_overloaded=True),
            ),
        )

        self.assertTrue(safety.is_hanging)
        self.assertTrue(safety.is_under_defended)
        self.assertFalse(safety.is_outnumbered)

    def test_pinned_attackers_are_not_effective(self) -> None:
        safety = piece_safety(attackers=(attacker(is_pinned=True),))

        self.assertFalse(safety.is_hanging)
        self.assertFalse(safety.is_under_defended)
        self.assertFalse(safety.is_outnumbered)

    def test_under_defended_when_effective_attackers_exceed_reliable_defenders(self) -> None:
        safety = piece_safety(
            attackers=(
                attacker(square=chess.B4),
                attacker(square=chess.H4, piece=chess.Piece(chess.BISHOP, chess.BLACK)),
            ),
            defenders=(defender(),),
        )

        self.assertTrue(safety.is_under_defended)

    def test_outnumbered_when_effective_attackers_exceed_all_defenders(self) -> None:
        safety = piece_safety(
            attackers=(
                attacker(square=chess.B4),
                attacker(square=chess.H4, piece=chess.Piece(chess.BISHOP, chess.BLACK)),
            ),
            defenders=(defender(),),
        )

        self.assertTrue(safety.is_outnumbered)

    def test_not_under_defended_or_outnumbered_when_defense_is_sufficient(self) -> None:
        safety = piece_safety(
            attackers=(attacker(),),
            defenders=(
                defender(square=chess.F3),
                defender(square=chess.E2),
            ),
        )

        self.assertFalse(safety.is_under_defended)
        self.assertFalse(safety.is_outnumbered)
