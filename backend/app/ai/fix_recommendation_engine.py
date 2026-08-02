"""Validate that LLM fixes are actionable Kubernetes recommendations."""

from __future__ import annotations

from app.ai.llm_client import LLMClientError
from app.models.investigation import Diagnosis


class FixRecommendationEngine:
    """Normalize commands and reject non-Kubernetes command recommendations."""

    def finalize(self, diagnosis: Diagnosis) -> Diagnosis:
        commands = [
            command.strip()
            for command in diagnosis.kubectl_commands
            if command.strip()
        ]
        if not commands or any(not command.startswith("kubectl ") for command in commands):
            raise LLMClientError("LLM returned invalid kubectl recommendations")
        return diagnosis.model_copy(
            update={"kubectl_commands": list(dict.fromkeys(commands))}
        )
