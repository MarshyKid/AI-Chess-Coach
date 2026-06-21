"""FastAPI request and response schemas for the local backend API."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class AnalyzeRequest(BaseModel):
    """Request body for deterministic PGN analysis."""

    pgn: str

    @field_validator("pgn")
    @classmethod
    def pgn_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pgn must not be blank")

        return value


class CoachRequest(BaseModel):
    """Request body for Ollama-backed coaching over analyzed evidence."""

    pgn: str
    question: str
    model: str | None = None
    ollama_base_url: str | None = None

    @field_validator("pgn")
    @classmethod
    def pgn_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pgn must not be blank")

        return value

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")

        return value


class HealthResponse(BaseModel):
    """Basic health response."""

    status: str


class CoachingMomentSummary(BaseModel):
    """Frontend-friendly coaching moment summary."""

    title: str
    explanation: str
    position_reference: str | None
    highlights: list[str]
    details: list[str]


class PatternSummary(BaseModel):
    """Frontend-friendly detected pattern summary."""

    pattern_type: str
    display_name: str
    frequency: int
    severity: float


class WeaknessProfileSummary(BaseModel):
    """Frontend-friendly weakness profile summary."""

    strengths: list[PatternSummary]
    execution_strengths: list[PatternSummary]
    weaknesses: list[PatternSummary]
    recurring_themes: list[PatternSummary]


class AnalyzeResponse(BaseModel):
    """Response body for deterministic analysis."""

    moves: int
    coaching_moments: list[CoachingMomentSummary]
    weakness_profile: WeaknessProfileSummary


class EvidenceSummary(BaseModel):
    """Summary of evidence supplied to the LLM coach."""

    coaching_moment_count: int
    has_weakness_profile: bool


class CoachResponse(BaseModel):
    """Response body for Ollama-backed coaching."""

    answer: str
    evidence_summary: EvidenceSummary
    coaching_moments: list[CoachingMomentSummary]
    weakness_profile: WeaknessProfileSummary
