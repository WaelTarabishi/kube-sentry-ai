from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.ai.agent import KubernetesAIAgent, get_ai_agent
from app.ai.llm_client import LLMClientError
from app.integrations.insforge import (
    AuthenticatedUser,
    InvestigationHistoryStore,
    get_current_user,
    get_history_store,
)
from app.models.investigation import InvestigationRequest, InvestigationResponse
from app.services.investigation_service import (
    InvestigationService,
    get_investigation_service,
)

router = APIRouter(tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResponse)
def investigate(
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    ai_agent: Annotated[KubernetesAIAgent, Depends(get_ai_agent)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    history: Annotated[InvestigationHistoryStore, Depends(get_history_store)],
    request: InvestigationRequest | None = None,
) -> InvestigationResponse:
    """Collect Kubernetes evidence and return a structured AI diagnosis."""

    request = request or InvestigationRequest()
    request_id = str(request.request_id)
    history.start(request_id=request_id, namespace=request.namespace, user=user)

    def report_progress(step: str, progress_state: str) -> None:
        history.progress(
            request_id=request_id,
            step=step,
            progress_state=progress_state,
            user=user,
        )

    investigation_payload = service.investigate(on_progress=report_progress)
    try:
        report_progress("ai_reasoning", "active")
        diagnosis = ai_agent.analyze(investigation_payload)
        report_progress("ai_reasoning", "completed")
    except LLMClientError as exc:
        logger.error("AI diagnosis unavailable: {}", exc)
        history.fail(
            request_id=request_id,
            message="AI diagnosis is temporarily unavailable.",
            user=user,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI diagnosis is temporarily unavailable.",
        ) from exc

    history.complete(request_id=request_id, diagnosis=diagnosis, user=user)

    return InvestigationResponse(
        status="success",
        investigation=investigation_payload,
        diagnosis=diagnosis,
    )
