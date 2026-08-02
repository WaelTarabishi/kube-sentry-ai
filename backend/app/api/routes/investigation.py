from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.investigation import InvestigationResponse
from app.services.investigation_service import (
    InvestigationService,
    get_investigation_service,
)

router = APIRouter(tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResponse)
def investigate(
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
) -> InvestigationResponse:
    """Collect Kubernetes evidence without performing AI analysis."""

    return InvestigationResponse(status="success", investigation=service.investigate())
