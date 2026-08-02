"""Small InsForge boundary for auth, investigation history, and progress writes."""

from dataclasses import dataclass
from typing import Any, Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.core.config import settings


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    access_token: str


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> AuthenticatedUser:
    """Validate the caller's access token against the configured InsForge project."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )
    if not settings.insforge_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="InsForge is not configured.",
        )

    try:
        response = httpx.get(
            f"{settings.insforge_base_url.rstrip('/')}/api/auth/sessions/current",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
            timeout=settings.insforge_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        logger.warning("InsForge authentication check failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired.",
        )
    if response.is_error:
        logger.warning("InsForge authentication returned HTTP {}", response.status_code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning("InsForge authentication returned invalid JSON")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service returned an invalid response.",
        ) from exc

    user = payload.get("user", {}) if isinstance(payload, dict) else {}
    user_id = user.get("id")
    email = user.get("email")
    if not isinstance(user_id, str) or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The authenticated user response was invalid.",
        )
    return AuthenticatedUser(user_id, email, credentials.credentials)


class InvestigationHistoryStore:
    """Persist investigation state through InsForge's authenticated records API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.insforge_base_url).rstrip("/")

    def start(
        self, *, request_id: str, namespace: str, user: AuthenticatedUser
    ) -> None:
        self._request(
            "POST",
            user,
            json=[
                {
                    "request_id": request_id,
                    "user_id": user.id,
                    "namespace": namespace,
                    "status": "running",
                    "progress_step": "checking_pods",
                    "progress_state": "active",
                }
            ],
        )

    def progress(
        self,
        *,
        request_id: str,
        step: str,
        progress_state: str,
        user: AuthenticatedUser,
    ) -> None:
        self._update(
            request_id,
            user,
            {"progress_step": step, "progress_state": progress_state},
        )

    def complete(
        self,
        *,
        request_id: str,
        diagnosis: Any,
        user: AuthenticatedUser,
    ) -> None:
        self._update(
            request_id,
            user,
            {
                "root_cause": diagnosis.root_cause,
                "confidence": diagnosis.confidence,
                "status": "success",
                "progress_step": "root_cause_found",
                "progress_state": "completed",
            },
        )

    def fail(
        self, *, request_id: str, message: str, user: AuthenticatedUser
    ) -> None:
        self._update(
            request_id,
            user,
            {
                "status": "failed",
                "progress_state": "failed",
                "error_message": message,
            },
        )

    def _update(
        self, request_id: str, user: AuthenticatedUser, values: dict[str, Any]
    ) -> None:
        self._request(
            "PATCH",
            user,
            params={"request_id": f"eq.{request_id}", "user_id": f"eq.{user.id}"},
            json=values,
        )

    def _request(
        self,
        method: str,
        user: AuthenticatedUser,
        **kwargs: Any,
    ) -> None:
        if not self.base_url:
            return
        try:
            response = httpx.request(
                method,
                f"{self.base_url}/api/database/records/investigations",
                headers={
                    "Authorization": f"Bearer {user.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=settings.insforge_timeout_seconds,
                **kwargs,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # Investigation remains available even if history/realtime is briefly degraded.
            logger.warning("Could not persist investigation progress to InsForge: {}", exc)


def get_history_store() -> InvestigationHistoryStore:
    return InvestigationHistoryStore()
