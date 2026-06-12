import unittest

import chess

from ai_chess_coach.models import MoveTransition, PositionAnalysis


class MoveTransitionTest(unittest.TestCase):
    def test_stores_move_and_before_after_positions(self) -> None:
        before_position = chess.Board()
        move = chess.Move.from_uci("e2e4")
        san = before_position.san(move)
        after_position = before_position.copy()
        after_position.push(move)

        transition = MoveTransition(
            ply=1,
            san=san,
            move=move,
            before_position=before_position,
            after_position=after_position,
        )

        self.assertEqual(transition.ply, 1)
        self.assertEqual(transition.san, "e4")
        self.assertEqual(transition.move, move)
        self.assertEqual(transition.before_position.fen(), chess.Board().fen())
        self.assertEqual(transition.after_position.piece_at(chess.E4), chess.Piece(chess.PAWN, chess.WHITE))

    def test_position_analysis_stores_board_fen_and_optional_feature_store(self) -> None:
        board = chess.Board()
        feature_store = object()

        position = PositionAnalysis(
            board=board,
            fen=board.fen(),
            feature_store=feature_store,
        )

        self.assertIs(position.board, board)
        self.assertEqual(position.fen, board.fen())
        self.assertIs(position.feature_store, feature_store)
