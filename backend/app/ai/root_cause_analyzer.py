"""Turn investigation evidence into a validated root-cause diagnosis."""

from __future__ import annotations

import json
from typing import Any, Protocol

from loguru import logger
from pydantic import ValidationError

from app.ai.llm_client import LLMClientError
from app.ai.prompt_builder import PromptBuilder
from app.models.investigation import Diagnosis


class CompletionClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


class RootCauseAnalyzer:
    """Ask the LLM to correlate evidence and enforce a structured result."""

    def __init__(
        self, client: CompletionClient, prompt_builder: PromptBuilder | None = None
    ) -> None:
        self.client = client
        self.prompt_builder = prompt_builder or PromptBuilder()

    def analyze(self, investigation: dict[str, Any]) -> Diagnosis:
        messages = self.prompt_builder.build(investigation)
        raw_diagnosis = self.client.complete(messages)
        try:
            payload = json.loads(_extract_json_object(raw_diagnosis))
            return Diagnosis.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            logger.error("LLM diagnosis did not match the required JSON schema")
            raise LLMClientError("LLM returned an invalid diagnosis") from exc


def _extract_json_object(content: str) -> str:
    """Accept plain JSON and defensively recover JSON from accidental code fences."""

    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object found")
    return stripped[start : end + 1]
