"""Detector framework for AI Chess Coach."""

from ai_chess_coach.detectors.base import BaseDetector
from ai_chess_coach.detectors.pipeline import DetectionPipeline
from ai_chess_coach.detectors.registry import DetectorRegistry

__all__ = [
    "BaseDetector",
    "DetectionPipeline",
    "DetectorRegistry",
]
