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
from app.kubernetes.cluster_registry import (
    ClusterAccessError,
    ClusterRegistry,
    get_cluster_registry,
)
from app.models.investigation import (
    ClusterListResponse,
    Diagnosis,
    InvestigationRequest,
    InvestigationResponse,
)
from app.services.investigation_service import (
    InvestigationService,
    get_investigation_service,
)

router = APIRouter(tags=["investigation"])


@router.get("/clusters", response_model=ClusterListResponse)
def list_clusters(
    registry: Annotated[ClusterRegistry, Depends(get_cluster_registry)],
    _: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ClusterListResponse:
    """Return every usable cluster from the backend's kubeconfig file."""

    try:
        return registry.list_clusters()
    except ClusterAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc


@router.post("/investigate", response_model=InvestigationResponse)
def investigate(
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    ai_agent: Annotated[KubernetesAIAgent, Depends(get_ai_agent)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    history: Annotated[InvestigationHistoryStore, Depends(get_history_store)],
    registry: Annotated[ClusterRegistry, Depends(get_cluster_registry)],
    request: InvestigationRequest,
) -> InvestigationResponse:
    """Collect Kubernetes evidence and return a structured AI diagnosis."""

    request_id = str(request.request_id)
    history.start(
        request_id=request_id,
        namespace=request.namespace,
        cluster_context=request.cluster_context,
        user=user,
    )

    def report_progress(step: str, progress_state: str) -> None:
        history.progress(
            request_id=request_id,
            step=step,
            progress_state=progress_state,
            user=user,
        )

    try:
        registry.validate_context(request.cluster_context)
        investigation_payload = service.for_context(request.cluster_context).investigate(
            on_progress=report_progress
        )
    except ClusterAccessError as exc:
        history.fail(request_id=request_id, message=exc.message, user=user)
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from exc

    if _is_cluster_healthy(investigation_payload):
        report_progress("ai_reasoning", "active")
        diagnosis = _healthy_diagnosis(request.cluster_context)
        report_progress("ai_reasoning", "completed")
        outcome = "healthy"
    else:
        outcome = "issue_found"
        try:
            report_progress("ai_reasoning", "active")
            diagnosis = ai_agent.analyze(investigation_payload)
            report_progress("ai_reasoning", "completed")
        except LLMClientError as exc:
            logger.error("AI diagnosis unavailable: {}", exc)
            message = "AI diagnosis is temporarily unavailable."
            history.fail(request_id=request_id, message=message, user=user)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "ai_unavailable",
                    "message": message,
                    "guidance": [
                        "Verify the OpenRouter API key and model settings.",
                        "Check the OpenRouter service status and try again.",
                    ],
                },
            ) from exc

    report_progress("root_cause_found", "completed")
    history.complete(request_id=request_id, diagnosis=diagnosis, user=user)

    return InvestigationResponse(
        status="success",
        outcome=outcome,
        cluster_context=request.cluster_context,
        investigation=investigation_payload,
        diagnosis=diagnosis,
    )


def _is_cluster_healthy(investigation: dict[str, dict]) -> bool:
    return all(
        investigation.get(section, {}).get("healthy") is True
        for section in ("pods", "events", "deployments", "network")
    )


def _healthy_diagnosis(context: str) -> Diagnosis:
    return Diagnosis(
        root_cause="No critical Kubernetes issues detected.",
        explanation="Pods, events, deployments, and networking checks did not report critical failures. The cluster appears healthy.",
        fix="No immediate fix is required. Continue monitoring the cluster.",
        kubectl_commands=[f"kubectl --context {context} get pods -A"],
        prevention_recommendation="Keep resource alerts, health probes, and regular cluster monitoring enabled.",
        confidence=95,
        confidence_reasoning=["All core investigation checks completed without critical findings."],
    )
