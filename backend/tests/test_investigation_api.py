from fastapi.testclient import TestClient

from app.ai.agent import get_ai_agent
from app.ai.llm_client import LLMClientError
from app.integrations.insforge import (
    AuthenticatedUser,
    get_current_user,
    get_history_store,
)
from app.main import app
from app.models.investigation import (
    ClusterListResponse,
    Diagnosis,
    KubernetesCluster,
)
from app.kubernetes.cluster_registry import get_cluster_registry
from app.services.investigation_service import get_investigation_service


class StubInvestigationService:
    def for_context(self, context: str):
        assert context == "kind-development"
        return self

    def investigate(self, on_progress=None) -> dict[str, dict]:
        if on_progress:
            on_progress("checking_pods", "active")
            on_progress("checking_pods", "completed")
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


class StubHistoryStore:
    def start(self, **kwargs) -> None:
        pass

    def progress(self, **kwargs) -> None:
        pass

    def complete(self, **kwargs) -> None:
        pass

    def fail(self, **kwargs) -> None:
        pass


class StubClusterRegistry:
    def list_clusters(self) -> ClusterListResponse:
        return ClusterListResponse(
            current_context="kind-development",
            clusters=[
                KubernetesCluster(
                    name="development",
                    server="https://127.0.0.1:6443",
                    contexts=["kind-development"],
                    selected_context="kind-development",
                    is_current=True,
                )
            ],
        )

    def validate_context(self, context: str) -> None:
        assert context == "kind-development"


def authenticated_user() -> AuthenticatedUser:
    return AuthenticatedUser("9d8795a8-18e8-4cb7-9c34-e47ad0fa7775", "dev@example.com", "token")


def override_dependencies(ai_agent) -> None:
    app.dependency_overrides[get_investigation_service] = StubInvestigationService
    app.dependency_overrides[get_ai_agent] = ai_agent
    app.dependency_overrides[get_current_user] = authenticated_user
    app.dependency_overrides[get_history_store] = StubHistoryStore
    app.dependency_overrides[get_cluster_registry] = StubClusterRegistry


def test_investigate_endpoint() -> None:
    override_dependencies(StubAIAgent)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/investigate",
                json={
                    "request_id": "d43add98-1c47-4b99-a696-41f759c00f4a",
                    "namespace": "all",
                    "cluster_context": "kind-development",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "outcome": "issue_found",
        "cluster_context": "kind-development",
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


def test_clusters_endpoint_lists_kubeconfig_clusters() -> None:
    override_dependencies(StubAIAgent)
    try:
        with TestClient(app) as client:
            response = client.get("/clusters")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["current_context"] == "kind-development"
    assert response.json()["clusters"][0]["name"] == "development"


def test_healthy_cluster_skips_ai_and_returns_empty_state() -> None:
    class HealthyInvestigationService(StubInvestigationService):
        def investigate(self, on_progress=None) -> dict[str, dict]:
            return {
                "pods": {"healthy": True},
                "logs": {"collected_pods": 0, "pods": []},
                "events": {"healthy": True},
                "deployments": {"healthy": True},
                "network": {"healthy": True},
            }

    class AIAgentThatMustNotRun:
        def analyze(self, investigation: dict[str, dict]) -> Diagnosis:
            raise AssertionError("AI should not run for a healthy cluster")

    override_dependencies(AIAgentThatMustNotRun)
    app.dependency_overrides[get_investigation_service] = HealthyInvestigationService
    try:
        with TestClient(app) as client:
            response = client.post(
                "/investigate",
                json={"cluster_context": "kind-development"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["outcome"] == "healthy"
    assert response.json()["diagnosis"]["root_cause"] == (
        "No critical Kubernetes issues detected."
    )


def test_investigate_returns_service_unavailable_when_ai_fails() -> None:
    class FailingAIAgent:
        def analyze(self, investigation: dict[str, dict]) -> Diagnosis:
            raise LLMClientError("OPENROUTER_API_KEY is not configured")

    override_dependencies(FailingAIAgent)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/investigate",
                json={"cluster_context": "kind-development"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ai_unavailable"


def test_investigate_requires_authentication() -> None:
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.post("/investigate")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required."}
