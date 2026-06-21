"""FastAPI app for the local AI Chess Coach backend."""

from __future__ import annotations

from typing import NoReturn

import chess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai_chess_coach.cli.analyze_pgn import build_default_game_analysis_pipeline
from ai_chess_coach.coaching import LLMChatCoach, LLMClient, format_coaching_moment_details
from ai_chess_coach.coaching.providers.errors import (
    EmptyLLMResponseError,
    LLMProviderError,
)
from ai_chess_coach.coaching.providers.ollama_client import (
    OllamaLLMClient,
    OllamaModelNotFoundError,
    OllamaProviderError,
    OllamaUnavailableError,
)
from ai_chess_coach.engine import StockfishEngine, StockfishUnavailableError
from ai_chess_coach.models import (
    CoachingMoment,
    DetectedPattern,
    GameAnalysisResult,
    WeaknessProfile,
    get_event_type_metadata,
)
from ai_chess_coach.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CoachRequest,
    CoachResponse,
    CoachingMomentSummary,
    EvidenceSummary,
    HealthResponse,
    PatternSummary,
    WeaknessProfileSummary,
)

LOCAL_DEV_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def create_app() -> FastAPI:
    """Create the local-development API app."""

    api = FastAPI(title="AI Chess Coach API")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_DEV_CORS_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @api.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @api.post("/analyze", response_model=AnalyzeResponse)
    def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
        try:
            result = analyze_pgn(request.pgn)
        except Exception as exc:
            _raise_http_error(exc)

        return _analysis_response(result)

    @api.post("/coach", response_model=CoachResponse)
    def coach(request: CoachRequest) -> CoachResponse:
        try:
            result = analyze_pgn(request.pgn)
            llm_client = build_ollama_client(
                model=request.model,
                base_url=request.ollama_base_url,
            )
            answer = LLMChatCoach(client=llm_client).respond(
                request.question,
                coaching_moments=result.coaching_moments,
                weakness_profile=result.weakness_profile,
            )
        except Exception as exc:
            _raise_http_error(exc)

        return CoachResponse(
            answer=answer,
            evidence_summary=EvidenceSummary(
                coaching_moment_count=len(result.coaching_moments),
                has_weakness_profile=_has_weakness_profile(result.weakness_profile),
            ),
            coaching_moments=_coaching_moment_summaries(result.coaching_moments),
            weakness_profile=_weakness_profile_summary(result.weakness_profile),
        )

    return api


def analyze_pgn(pgn: str) -> GameAnalysisResult:
    """Analyze one PGN string with the default backend pipeline."""

    engine: StockfishEngine | None = None
    try:
        engine = StockfishEngine()
        pipeline = build_default_game_analysis_pipeline(engine)
        return pipeline.analyze_pgn(pgn)
    finally:
        if engine is not None:
            engine.close()


def build_ollama_client(
    *,
    model: str | None,
    base_url: str | None,
) -> LLMClient:
    """Build the Ollama client used by the local API coach endpoint."""

    return OllamaLLMClient(model=model, base_url=base_url)


def _analysis_response(result: GameAnalysisResult) -> AnalyzeResponse:
    return AnalyzeResponse(
        moves=len(result.transitions),
        coaching_moments=_coaching_moment_summaries(result.coaching_moments),
        weakness_profile=_weakness_profile_summary(result.weakness_profile),
    )


def _coaching_moment_summaries(
    moments: tuple[CoachingMoment, ...],
) -> list[CoachingMomentSummary]:
    return [
        CoachingMomentSummary(
            title=moment.title,
            explanation=moment.explanation,
            position_reference=moment.position_reference,
            highlights=[chess.square_name(square) for square in moment.highlights],
            details=list(format_coaching_moment_details(moment)),
        )
        for moment in moments
    ]


def _weakness_profile_summary(profile: WeaknessProfile) -> WeaknessProfileSummary:
    return WeaknessProfileSummary(
        strengths=_pattern_summaries(profile.strengths),
        execution_strengths=_pattern_summaries(profile.execution_strengths),
        weaknesses=_pattern_summaries(profile.weaknesses),
        recurring_themes=_pattern_summaries(profile.recurring_themes),
    )


def _pattern_summaries(patterns: tuple[DetectedPattern, ...]) -> list[PatternSummary]:
    return [
        PatternSummary(
            pattern_type=pattern.pattern_type,
            display_name=get_event_type_metadata(pattern.pattern_type).display_name,
            frequency=pattern.frequency,
            severity=pattern.severity,
        )
        for pattern in patterns
    ]


def _has_weakness_profile(profile: WeaknessProfile) -> bool:
    return bool(
        profile.strengths
        or profile.execution_strengths
        or profile.weaknesses
        or profile.recurring_themes
    )


def _raise_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid PGN or analysis input: {exc}",
        ) from exc
    if isinstance(exc, StockfishUnavailableError):
        raise HTTPException(
            status_code=503,
            detail=f"Stockfish unavailable: {exc}",
        ) from exc
    if isinstance(exc, OllamaUnavailableError):
        raise HTTPException(
            status_code=503,
            detail=f"Ollama unavailable: {exc}",
        ) from exc
    if isinstance(exc, OllamaModelNotFoundError):
        raise HTTPException(
            status_code=503,
            detail=f"Ollama model not found: {exc}",
        ) from exc
    if isinstance(exc, EmptyLLMResponseError):
        raise HTTPException(
            status_code=502,
            detail=f"Empty LLM response: {exc}",
        ) from exc
    if isinstance(exc, (OllamaProviderError, LLMProviderError)):
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error: {exc}",
        ) from exc

    raise HTTPException(
        status_code=500,
        detail="Unexpected API error.",
    ) from exc


app = create_app()
