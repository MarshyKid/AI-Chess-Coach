"""End-to-end game analysis pipeline orchestration."""

from __future__ import annotations

from ai_chess_coach.analysis.replay import replay_pgn_string
from ai_chess_coach.coaching import ReviewGenerator
from ai_chess_coach.detectors import DetectionPipeline
from ai_chess_coach.engine.verifier import EventVerifier
from ai_chess_coach.models import GameAnalysisResult
from ai_chess_coach.profiling import PatternAggregator, WeaknessProfileBuilder


class GameAnalysisPipeline:
    """Orchestrates PGN replay through verification, profiling, and review generation."""

    def __init__(
        self,
        detection_pipeline: DetectionPipeline,
        event_verifier: EventVerifier,
        pattern_aggregator: PatternAggregator | None = None,
        weakness_profile_builder: WeaknessProfileBuilder | None = None,
        review_generator: ReviewGenerator | None = None,
    ) -> None:
        self._detection_pipeline = detection_pipeline
        self._event_verifier = event_verifier
        self._pattern_aggregator = pattern_aggregator or PatternAggregator()
        self._weakness_profile_builder = weakness_profile_builder or WeaknessProfileBuilder()
        self._review_generator = review_generator or ReviewGenerator()

    def analyze_pgn(self, pgn_text: str) -> GameAnalysisResult:
        """Analyze one PGN string and return all structured pipeline outputs."""

        transitions = tuple(replay_pgn_string(pgn_text))

        detected_events = tuple(
            event
            for transition in transitions
            for event in self._detection_pipeline.run(transition)
        )
        verified_events = tuple(
            self._event_verifier.verify(event)
            for event in detected_events
        )
        detected_patterns = tuple(self._pattern_aggregator.aggregate(verified_events))
        weakness_profile = self._weakness_profile_builder.build(detected_patterns)
        coaching_moments = tuple(self._review_generator.generate(verified_events))

        return GameAnalysisResult(
            transitions=transitions,
            detected_events=detected_events,
            verified_events=verified_events,
            detected_patterns=detected_patterns,
            weakness_profile=weakness_profile,
            coaching_moments=coaching_moments,
        )
