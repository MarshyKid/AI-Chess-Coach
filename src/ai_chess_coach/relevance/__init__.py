"""Shared relevance policies for downstream coaching/profile outputs."""

from ai_chess_coach.relevance.coaching_relevance_policy import CoachingRelevancePolicy
from ai_chess_coach.relevance.execution_strength_policy import ExecutionStrengthPolicy

__all__ = [
    "CoachingRelevancePolicy",
    "ExecutionStrengthPolicy",
]
