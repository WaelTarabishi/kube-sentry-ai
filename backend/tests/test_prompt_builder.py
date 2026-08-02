import json

from app.ai.prompt_builder import PromptBuilder


def test_prompt_builder_includes_all_evidence_sections_deterministically() -> None:
    investigation = {
        "pods": {"status": "CrashLoopBackOff"},
        "logs": {"error": "DATABASE_URL missing"},
        "events": {"summary": {"BackOff": 4}},
        "deployments": {"healthy": False},
        "network": {"healthy": True},
    }

    first = PromptBuilder().build(investigation)
    second = PromptBuilder().build(investigation)

    assert first == second
    assert [message["role"] for message in first] == ["system", "user"]
    assert "Senior Kubernetes Site Reliability Engineer" in first[0]["content"]
    for heading in (
        "## Pod Status",
        "## Logs",
        "## Events",
        "## Deployment Health",
        "## Networking Findings",
    ):
        assert heading in first[1]["content"]
    assert (
        json.dumps(investigation["logs"], indent=2, sort_keys=True)
        in first[1]["content"]
    )
