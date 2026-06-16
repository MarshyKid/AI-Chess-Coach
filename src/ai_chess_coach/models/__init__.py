"""Core domain models for AI Chess Coach."""

from ai_chess_coach.models.candidate_move import CandidateMove
from ai_chess_coach.models.coaching_moment import CoachingMoment
from ai_chess_coach.models.detected_pattern import DetectedPattern
from ai_chess_coach.models.detected_event import DetectedEvent
from ai_chess_coach.models.engine_assessment import EngineAssessment
from ai_chess_coach.models.engine_score import EngineScore, MATE_RANK_BASE, ScoreKind
from ai_chess_coach.models.event_metadata import EventMetadata
from ai_chess_coach.models.event_type_metadata import (
    EventPolarity,
    EventTypeMetadata,
    VerificationKind,
    get_event_type_metadata,
    registered_event_type_metadata,
)
from ai_chess_coach.models.game_analysis_result import GameAnalysisResult
from ai_chess_coach.models.move_transition import MoveTransition
from ai_chess_coach.models.piece_safety import (
    AttackerInfo,
    DefenderInfo,
    PieceSafety,
)
from ai_chess_coach.models.position_analysis import PositionAnalysis
from ai_chess_coach.models.verified_event import VerifiedEvent
from ai_chess_coach.models.weakness_profile import WeaknessProfile

__all__ = [
    "AttackerInfo",
    "CandidateMove",
    "CoachingMoment",
    "DefenderInfo",
    "DetectedPattern",
    "DetectedEvent",
    "EngineAssessment",
    "EngineScore",
    "EventPolarity",
    "EventMetadata",
    "EventTypeMetadata",
    "GameAnalysisResult",
    "MATE_RANK_BASE",
    "MoveTransition",
    "PieceSafety",
    "PositionAnalysis",
    "ScoreKind",
    "VerifiedEvent",
    "VerificationKind",
    "WeaknessProfile",
    "get_event_type_metadata",
    "registered_event_type_metadata",
]
