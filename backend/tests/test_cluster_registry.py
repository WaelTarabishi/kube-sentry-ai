import json

import pytest

from app.kubernetes.cluster_registry import ClusterAccessError, ClusterRegistry
from app.kubernetes.kubectl_executor import KubectlResult


class FakeExecutor:
    def __init__(self, context: str | None = None, connection_error: str = "") -> None:
        self.context = context
        self.connection_error = connection_error

    def with_context(self, context: str):
        return FakeExecutor(context, self.connection_error)

    def execute(self, *arguments: str) -> KubectlResult:
        if arguments[0] == "config":
            payload = {
                "current-context": "kind-development",
                "clusters": [
                    {
                        "name": "development",
                        "cluster": {"server": "https://127.0.0.1:6443"},
                    },
                    {
                        "name": "staging",
                        "cluster": {"server": "https://staging.example.test"},
                    },
                ],
                "contexts": [
                    {
                        "name": "kind-development",
                        "context": {"cluster": "development", "user": "kind-user"},
                    },
                    {
                        "name": "staging-admin",
                        "context": {"cluster": "staging", "user": "staging-user"},
                    },
                ],
            }
            return KubectlResult(
                ["kubectl", *arguments], True, json.dumps(payload), return_code=0
            )
        return KubectlResult(
            ["kubectl", *arguments],
            not self.connection_error,
            stdout="{}" if not self.connection_error else "",
            stderr=self.connection_error,
            return_code=0 if not self.connection_error else 1,
        )


class EmptyConfigExecutor:
    def execute(self, *arguments: str) -> KubectlResult:
        return KubectlResult(
            ["kubectl", *arguments],
            True,
            stdout=json.dumps({"clusters": [], "contexts": []}),
            return_code=0,
        )


def test_registry_lists_every_usable_kubeconfig_cluster() -> None:
    response = ClusterRegistry(FakeExecutor()).list_clusters()

    assert [cluster.name for cluster in response.clusters] == [
        "development",
        "staging",
    ]
    assert response.clusters[0].is_current is True
    assert response.clusters[1].selected_context == "staging-admin"


def test_registry_explains_empty_kubeconfig() -> None:
    with pytest.raises(ClusterAccessError) as caught:
        ClusterRegistry(EmptyConfigExecutor()).list_clusters()

    assert caught.value.code == "no_kubeconfig_clusters"
    assert "No usable Kubernetes clusters" in caught.value.message


def test_registry_rejects_unknown_context() -> None:
    with pytest.raises(ClusterAccessError) as caught:
        ClusterRegistry(FakeExecutor()).validate_context("deleted-context")

    assert caught.value.code == "unknown_cluster_context"
    assert caught.value.status_code == 400


def test_registry_returns_friendly_unreachable_error() -> None:
    registry = ClusterRegistry(FakeExecutor(connection_error="dial tcp: connection refused"))

    with pytest.raises(ClusterAccessError) as caught:
        registry.validate_context("kind-development")

    assert caught.value.code == "cluster_unreachable"
    assert "Unable to connect" in caught.value.message
