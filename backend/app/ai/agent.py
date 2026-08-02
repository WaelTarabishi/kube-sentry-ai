"""High-level Kubernetes diagnosis workflow."""

from __future__ import annotations

from typing import Any

from app.ai.confidence_engine import ConfidenceEngine
from app.ai.fix_recommendation_engine import FixRecommendationEngine
from app.ai.llm_client import OpenRouterClient
from app.ai.root_cause_analyzer import RootCauseAnalyzer
from app.core.config import settings
from app.models.investigation import Diagnosis


class KubernetesAIAgent:
    """Coordinate root-cause, fix, and confidence processing."""

    def __init__(
        self,
        analyzer: RootCauseAnalyzer,
        fix_engine: FixRecommendationEngine | None = None,
        confidence_engine: ConfidenceEngine | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.fix_engine = fix_engine or FixRecommendationEngine()
        self.confidence_engine = confidence_engine or ConfidenceEngine()

    def analyze(self, investigation: dict[str, Any]) -> Diagnosis:
        diagnosis = self.analyzer.analyze(investigation)
        diagnosis = self.fix_engine.finalize(diagnosis)
        return self.confidence_engine.finalize(diagnosis)


def get_ai_agent() -> KubernetesAIAgent:
    """Build the AI agent from environment-backed application settings."""

    client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
        timeout_seconds=settings.openrouter_timeout_seconds,
        max_retries=settings.openrouter_max_retries,
    )
    return KubernetesAIAgent(RootCauseAnalyzer(client))
