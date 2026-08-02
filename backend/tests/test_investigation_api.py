from fastapi.testclient import TestClient

from app.ai.agent import get_ai_agent
from app.ai.llm_client import LLMClientError
from app.main import app
from app.models.investigation import Diagnosis
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


class StubAIAgent:
    def analyze(self, investigation: dict[str, dict]) -> Diagnosis:
        assert investigation["pods"] == {}
        return Diagnosis(
            root_cause="DATABASE_URL is missing.",
            explanation="The application fails during startup before becoming ready.",
            fix="Add DATABASE_URL to the payment-service deployment.",
            kubectl_commands=[
                "kubectl set env deployment/payment-service DATABASE_URL=<value>"
            ],
            prevention_recommendation="Validate required configuration during deployment.",
            confidence=92,
            confidence_reasoning=["The startup log names the missing variable."],
        )


def test_investigate_endpoint() -> None:
    app.dependency_overrides[get_investigation_service] = StubInvestigationService
    app.dependency_overrides[get_ai_agent] = StubAIAgent
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
        "diagnosis": {
            "root_cause": "DATABASE_URL is missing.",
            "explanation": "The application fails during startup before becoming ready.",
            "fix": "Add DATABASE_URL to the payment-service deployment.",
            "kubectl_commands": [
                "kubectl set env deployment/payment-service DATABASE_URL=<value>"
            ],
            "prevention_recommendation": "Validate required configuration during deployment.",
            "confidence": 92,
            "confidence_reasoning": ["The startup log names the missing variable."],
        },
    }


def test_investigate_returns_service_unavailable_when_ai_fails() -> None:
    class FailingAIAgent:
        def analyze(self, investigation: dict[str, dict]) -> Diagnosis:
            raise LLMClientError("OPENROUTER_API_KEY is not configured")

    app.dependency_overrides[get_investigation_service] = StubInvestigationService
    app.dependency_overrides[get_ai_agent] = FailingAIAgent
    try:
        with TestClient(app) as client:
            response = client.post("/investigate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "AI diagnosis is temporarily unavailable."}
