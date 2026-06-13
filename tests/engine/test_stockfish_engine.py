import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import Mock, patch

import chess
import chess.engine

from ai_chess_coach.engine import (
    StockfishAnalysis,
    StockfishEngine,
    StockfishUnavailableError,
)


class StockfishEngineTest(unittest.TestCase):
    def test_can_be_constructed_with_explicit_path(self) -> None:
        engine_process = Mock()

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ) as popen_uci:
            engine = StockfishEngine("/usr/local/bin/stockfish")

        popen_uci.assert_called_once_with("/usr/local/bin/stockfish")
        self.assertEqual(engine.engine_path, "/usr/local/bin/stockfish")
        engine.close()

    def test_accepts_path_like_explicit_path(self) -> None:
        engine_process = Mock()

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ) as popen_uci:
            engine = StockfishEngine(Path("/usr/local/bin/stockfish"))

        popen_uci.assert_called_once_with("/usr/local/bin/stockfish")
        engine.close()

    def test_uses_stockfish_path_environment_variable(self) -> None:
        engine_process = Mock()

        with patch.dict(os.environ, {"STOCKFISH_PATH": "/env/stockfish"}), patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ) as popen_uci:
            engine = StockfishEngine()

        popen_uci.assert_called_once_with("/env/stockfish")
        engine.close()

    def test_uses_stockfish_from_path_when_no_explicit_or_environment_path(self) -> None:
        engine_process = Mock()

        with patch.dict(os.environ, {}, clear=True), patch(
            "ai_chess_coach.engine.stockfish_engine.shutil.which",
            return_value="/path/stockfish",
        ), patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ) as popen_uci:
            engine = StockfishEngine()

        popen_uci.assert_called_once_with("/path/stockfish")
        engine.close()

    def test_missing_engine_path_raises_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "ai_chess_coach.engine.stockfish_engine.shutil.which",
            return_value=None,
        ):
            with self.assertRaisesRegex(
                StockfishUnavailableError,
                "Pass engine_path or set STOCKFISH_PATH",
            ):
                StockfishEngine()

    def test_startup_failure_is_wrapped_as_unavailable_error(self) -> None:
        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            side_effect=OSError("cannot execute"),
        ):
            with self.assertRaisesRegex(
                StockfishUnavailableError,
                "/bad/stockfish",
            ):
                StockfishEngine("/bad/stockfish")

    def test_configure_failure_closes_engine_before_reraising(self) -> None:
        engine_process = Mock()
        engine_process.configure.side_effect = RuntimeError("bad option")

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            with self.assertRaisesRegex(RuntimeError, "bad option"):
                StockfishEngine("/stockfish", engine_options={"Hash": 16})

        engine_process.quit.assert_called_once_with()

    def test_evaluate_fen_returns_structured_analysis(self) -> None:
        engine_process = Mock()
        score = chess.engine.PovScore(chess.engine.Cp(23), chess.WHITE)
        pv = [
            chess.Move.from_uci("e2e4"),
            chess.Move.from_uci("e7e5"),
        ]
        engine_process.analyse.return_value = {
            "score": score,
            "pv": pv,
            "depth": 7,
        }

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            engine = StockfishEngine("/stockfish")
            analysis = engine.evaluate_fen(chess.STARTING_FEN, depth=7)

        self.assertIsInstance(analysis, StockfishAnalysis)
        self.assertEqual(analysis.fen, chess.STARTING_FEN)
        self.assertEqual(analysis.score, score)
        self.assertEqual(analysis.best_move, chess.Move.from_uci("e2e4"))
        self.assertEqual(analysis.principal_variation, tuple(pv))
        self.assertEqual(analysis.depth, 7)
        board_arg, limit_arg = engine_process.analyse.call_args.args
        self.assertEqual(board_arg.fen(), chess.STARTING_FEN)
        self.assertEqual(limit_arg.depth, 7)
        engine.close()

    def test_evaluate_fen_handles_absent_principal_variation(self) -> None:
        engine_process = Mock()
        engine_process.analyse.return_value = {"score": None, "depth": 5}

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            engine = StockfishEngine("/stockfish")
            analysis = engine.evaluate_fen(chess.STARTING_FEN)

        self.assertIsNone(analysis.best_move)
        self.assertEqual(analysis.principal_variation, ())
        engine.close()

    def test_best_move_returns_chess_move(self) -> None:
        engine_process = Mock()
        move = chess.Move.from_uci("e2e4")
        engine_process.play.return_value = Mock(move=move)

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            engine = StockfishEngine("/stockfish")
            best_move = engine.best_move(chess.STARTING_FEN, depth=4)

        self.assertEqual(best_move, move)
        board_arg, limit_arg = engine_process.play.call_args.args
        self.assertEqual(board_arg.fen(), chess.STARTING_FEN)
        self.assertEqual(limit_arg.depth, 4)
        engine.close()

    def test_principal_variation_returns_tuple_of_moves(self) -> None:
        engine_process = Mock()
        pv = [
            chess.Move.from_uci("d2d4"),
            chess.Move.from_uci("d7d5"),
        ]
        engine_process.analyse.return_value = {"pv": pv}

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            engine = StockfishEngine("/stockfish")
            principal_variation = engine.principal_variation(chess.STARTING_FEN)

        self.assertEqual(principal_variation, tuple(pv))
        engine.close()

    def test_close_quits_engine_once(self) -> None:
        engine_process = Mock()

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            engine = StockfishEngine("/stockfish")

        engine.close()
        engine.close()

        engine_process.quit.assert_called_once_with()

    def test_context_manager_closes_engine(self) -> None:
        engine_process = Mock()

        with patch(
            "ai_chess_coach.engine.stockfish_engine.chess.engine.SimpleEngine.popen_uci",
            return_value=engine_process,
        ):
            with StockfishEngine("/stockfish") as engine:
                self.assertIsNotNone(engine)

        engine_process.quit.assert_called_once_with()

    def test_real_stockfish_smoke_test_skips_when_unavailable(self) -> None:
        stockfish_path = os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish")
        if stockfish_path is None:
            self.skipTest("Stockfish binary not available.")

        try:
            with StockfishEngine(stockfish_path, depth=1) as engine:
                analysis = engine.evaluate_fen(chess.STARTING_FEN, depth=1)
        except StockfishUnavailableError as exc:
            self.skipTest(f"Stockfish could not be started: {exc}")

        self.assertEqual(analysis.fen, chess.STARTING_FEN)

    def test_detectors_do_not_import_engine_or_stockfish(self) -> None:
        detector_dir = Path(__file__).parents[2] / "src" / "ai_chess_coach" / "detectors"

        for detector_file in detector_dir.glob("*.py"):
            source = detector_file.read_text(encoding="utf-8").lower()
            self.assertNotIn("ai_chess_coach.engine", source, detector_file.name)
            self.assertNotIn("stockfish", source, detector_file.name)

    def test_engine_wrapper_does_not_introduce_llm_calls(self) -> None:
        source = (
            Path(__file__).parents[2]
            / "src"
            / "ai_chess_coach"
            / "engine"
            / "stockfish_engine.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("openai", source)
        self.assertNotIn("llm", source)
