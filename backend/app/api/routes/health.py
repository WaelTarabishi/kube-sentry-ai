from fastapi import APIRouter

from app.core.config import settings
from app.models.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service=settings.service_name)

