"""Detector framework for AI Chess Coach."""

from ai_chess_coach.detectors.base import BaseDetector
from ai_chess_coach.detectors.fork_detector import ForkDetector
from ai_chess_coach.detectors.hanging_piece_detector import HangingPieceDetector
from ai_chess_coach.detectors.pipeline import DetectionPipeline
from ai_chess_coach.detectors.registry import DetectorRegistry

__all__ = [
    "BaseDetector",
    "DetectionPipeline",
    "DetectorRegistry",
    "ForkDetector",
    "HangingPieceDetector",
]
