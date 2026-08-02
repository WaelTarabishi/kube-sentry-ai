"""API models for Kubernetes evidence gathering and AI diagnosis."""

from uuid import UUID, uuid4
from typing import Any, Literal

from pydantic import BaseModel, Field


class InvestigationPayload(BaseModel):
    pods: dict[str, Any]
    logs: dict[str, Any]
    events: dict[str, Any]
    deployments: dict[str, Any]
    network: dict[str, Any]


class Diagnosis(BaseModel):
    """Structured, user-facing result produced by the Kubernetes AI agent."""

    root_cause: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    fix: str = Field(min_length=1)
    kubectl_commands: list[str] = Field(min_length=1)
    prevention_recommendation: str = Field(min_length=1)
    confidence: int = Field(ge=0, le=100)
    confidence_reasoning: list[str] = Field(min_length=1)


class InvestigationResponse(BaseModel):
    status: Literal["success"]
    investigation: InvestigationPayload
    diagnosis: Diagnosis


class InvestigationRequest(BaseModel):
    """Client context used for realtime progress and history correlation."""

    request_id: UUID = Field(default_factory=uuid4)
    namespace: str = Field(default="all", min_length=1, max_length=253)
