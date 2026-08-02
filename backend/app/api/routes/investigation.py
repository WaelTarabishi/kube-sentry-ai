from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.ai.agent import KubernetesAIAgent, get_ai_agent
from app.ai.llm_client import LLMClientError
from app.models.investigation import InvestigationResponse
from app.services.investigation_service import (
    InvestigationService,
    get_investigation_service,
)

router = APIRouter(tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResponse)
def investigate(
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    ai_agent: Annotated[KubernetesAIAgent, Depends(get_ai_agent)],
) -> InvestigationResponse:
    """Collect Kubernetes evidence and return a structured AI diagnosis."""

    investigation_payload = service.investigate()
    try:
        diagnosis = ai_agent.analyze(investigation_payload)
    except LLMClientError as exc:
        logger.error("AI diagnosis unavailable: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI diagnosis is temporarily unavailable.",
        ) from exc

    return InvestigationResponse(
        status="success",
        investigation=investigation_payload,
        diagnosis=diagnosis,
    )
