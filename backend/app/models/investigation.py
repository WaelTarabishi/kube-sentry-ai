"""API response models for Kubernetes evidence gathering."""

from typing import Any, Literal

from pydantic import BaseModel


class InvestigationPayload(BaseModel):
    pods: dict[str, Any]
    logs: dict[str, Any]
    events: dict[str, Any]
    deployments: dict[str, Any]
    network: dict[str, Any]


class InvestigationResponse(BaseModel):
    status: Literal["success"]
    investigation: InvestigationPayload
