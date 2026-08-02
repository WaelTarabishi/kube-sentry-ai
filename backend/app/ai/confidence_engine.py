"""Finalize the confidence explanation returned by the reasoning model."""

from __future__ import annotations

from app.ai.llm_client import LLMClientError
from app.models.investigation import Diagnosis


class ConfidenceEngine:
    """Require an explainable confidence score rather than a bare percentage."""

    def finalize(self, diagnosis: Diagnosis) -> Diagnosis:
        reasons = [
            reason.strip()
            for reason in diagnosis.confidence_reasoning
            if reason.strip()
        ]
        if not reasons:
            raise LLMClientError("LLM returned confidence without evidence reasoning")
        return diagnosis.model_copy(
            update={"confidence_reasoning": list(dict.fromkeys(reasons))}
        )
