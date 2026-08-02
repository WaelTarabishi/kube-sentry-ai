from fastapi.testclient import TestClient

from app.main import app
from app.services.investigation_service import get_investigation_service


class StubInvestigationService:
    def investigate(self) -> dict[str, dict]:
        return {
            "pods": {},
            "logs": {},
            "events": {},
            "deployments": {},
            "network": {},
        }


def test_investigate_endpoint() -> None:
    app.dependency_overrides[get_investigation_service] = StubInvestigationService
    try:
        with TestClient(app) as client:
            response = client.post("/investigate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "investigation": {
            "pods": {},
            "logs": {},
            "events": {},
            "deployments": {},
            "network": {},
        },
    }
