import json

import pytest

from app.ai.agent import KubernetesAIAgent
from app.ai.llm_client import LLMClientError
from app.ai.root_cause_analyzer import RootCauseAnalyzer


class FakeCompletionClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[dict[str, str]] | None = None

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return self.response


def test_ai_agent_returns_correlated_structured_diagnosis() -> None:
    response = json.dumps(
        {
            "root_cause": "DATABASE_URL is missing from the payment-service container.",
            "explanation": (
                "The pod is in CrashLoopBackOff with five restarts, and its startup "
                "log explicitly reports the missing variable."
            ),
            "fix": "Add DATABASE_URL from a Kubernetes Secret and restart the rollout.",
            "kubectl_commands": [
                "kubectl set env deployment/payment-service -n default --from=secret/payment-db",
                "kubectl rollout status deployment/payment-service -n default",
            ],
            "prevention_recommendation": (
                "Validate required environment variables in CI and add a startup probe."
            ),
            "confidence": 92,
            "confidence_reasoning": [
                "CrashLoopBackOff and repeated restarts confirm a startup failure.",
                "The application log explicitly identifies DATABASE_URL as missing.",
            ],
        }
    )
    client = FakeCompletionClient(response)
    agent = KubernetesAIAgent(RootCauseAnalyzer(client))
    evidence = {
        "pods": {
            "problematic_pods": [
                {
                    "name": "payment-service",
                    "status": "CrashLoopBackOff",
                    "restart_count": 5,
                }
            ]
        },
        "logs": {"pods": [{"lines": ["DATABASE_URL environment variable is missing"]}]},
        "events": {},
        "deployments": {"healthy": False},
        "network": {"healthy": True},
    }

    diagnosis = agent.analyze(evidence)

    assert diagnosis.root_cause.startswith("DATABASE_URL")
    assert diagnosis.confidence == 92
    assert len(diagnosis.kubectl_commands) == 2
    assert client.messages is not None
    assert "CrashLoopBackOff" in client.messages[1]["content"]
    assert "DATABASE_URL" in client.messages[1]["content"]


def test_ai_agent_rejects_non_kubectl_commands() -> None:
    response = json.dumps(
        {
            "root_cause": "Unknown startup error",
            "explanation": "The container exits during startup.",
            "fix": "Inspect the local host.",
            "kubectl_commands": ["docker logs payment-service"],
            "prevention_recommendation": "Add health checks.",
            "confidence": 40,
            "confidence_reasoning": ["Only one signal is available."],
        }
    )

    with pytest.raises(LLMClientError, match="kubectl"):
        KubernetesAIAgent(RootCauseAnalyzer(FakeCompletionClient(response))).analyze({})


def test_root_cause_analyzer_rejects_invalid_json() -> None:
    analyzer = RootCauseAnalyzer(FakeCompletionClient("not json"))

    with pytest.raises(LLMClientError, match="invalid diagnosis"):
        analyzer.analyze({})
