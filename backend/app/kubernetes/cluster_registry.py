"""Discover kubeconfig clusters and validate access to a selected context."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.kubernetes.kubectl_executor import KubectlExecutor
from app.models.investigation import ClusterListResponse, KubernetesCluster
from app.core.config import settings


@dataclass(frozen=True, slots=True)
class ClusterAccessError(RuntimeError):
    code: str
    message: str
    guidance: list[str]
    status_code: int = 503

    def __str__(self) -> str:
        return self.message

    def to_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "guidance": self.guidance,
        }


class ClusterRegistry:
    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def list_clusters(self) -> ClusterListResponse:
        result = self.executor.execute("config", "view", "-o", "json")
        if not result.success:
            raise _classify_kubectl_error(result.stderr)

        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("kubectl returned invalid kubeconfig JSON")
            raise ClusterAccessError(
                code="invalid_kubeconfig",
                message="The Kubernetes configuration could not be read.",
                guidance=[
                    "Verify that the kubeconfig file contains valid YAML.",
                    "Run 'kubectl config view' to inspect it.",
                ],
            ) from exc

        if not isinstance(payload, dict):
            raise ClusterAccessError(
                code="invalid_kubeconfig",
                message="The Kubernetes configuration has an unexpected format.",
                guidance=["Run 'kubectl config view' and verify the kubeconfig file."],
            )

        current_context = _string_or_none(payload.get("current-context"))
        contexts_by_cluster: dict[str, list[str]] = {}
        for item in payload.get("contexts", []):
            if not isinstance(item, dict):
                continue
            context_name = _string_or_none(item.get("name"))
            context_data = item.get("context", {})
            cluster_name = (
                _string_or_none(context_data.get("cluster"))
                if isinstance(context_data, dict)
                else None
            )
            if context_name and cluster_name:
                contexts_by_cluster.setdefault(cluster_name, []).append(context_name)

        clusters: list[KubernetesCluster] = []
        for item in payload.get("clusters", []):
            if not isinstance(item, dict):
                continue
            name = _string_or_none(item.get("name"))
            if not name:
                continue
            contexts = contexts_by_cluster.get(name, [])
            if not contexts:
                # A cluster without a context has no credentials/user binding and
                # therefore cannot safely be selected for an investigation.
                continue
            cluster_data = item.get("cluster", {})
            server = (
                str(cluster_data.get("server", ""))
                if isinstance(cluster_data, dict)
                else ""
            )
            selected_context = (
                current_context if current_context in contexts else contexts[0]
            )
            clusters.append(
                KubernetesCluster(
                    name=name,
                    server=server,
                    contexts=contexts,
                    selected_context=selected_context,
                    is_current=current_context in contexts,
                )
            )

        clusters.sort(key=lambda cluster: (not cluster.is_current, cluster.name.lower()))
        if not clusters:
            raise ClusterAccessError(
                code="no_kubeconfig_clusters",
                message="No usable Kubernetes clusters were found in the kubeconfig file.",
                guidance=[
                    "Verify the KUBECONFIG_PATH setting.",
                    "Add a context with 'kubectl config set-context'.",
                    "Run 'kubectl config get-contexts' on the backend machine.",
                ],
            )
        return ClusterListResponse(clusters=clusters, current_context=current_context)

    def validate_context(self, context: str) -> None:
        available = self.list_clusters()
        valid_contexts = {
            item for cluster in available.clusters for item in cluster.contexts
        }
        if context not in valid_contexts:
            raise ClusterAccessError(
                code="unknown_cluster_context",
                message="The selected Kubernetes cluster is no longer available.",
                guidance=[
                    "Refresh the cluster list.",
                    "Verify the context still exists in your kubeconfig file.",
                ],
                status_code=400,
            )

        result = self.executor.with_context(context).execute(
            "version", "--request-timeout=10s", "-o", "json"
        )
        if not result.success:
            raise _classify_kubectl_error(result.stderr)


def _classify_kubectl_error(stderr: str) -> ClusterAccessError:
    error = stderr.strip()
    lowered = error.lower()
    if "was not found" in lowered and "kubectl" in lowered:
        return ClusterAccessError(
            code="kubectl_not_found",
            message="kubectl is not installed or is not available to the backend.",
            guidance=[
                "Install kubectl on the backend machine.",
                "Verify that kubectl is available on PATH.",
            ],
        )
    if any(
        signal in lowered
        for signal in (
            "no configuration has been provided",
            "no such file or directory",
            "cannot find the file",
            "kubeconfig file was not found",
        )
    ):
        return ClusterAccessError(
            code="missing_kubeconfig",
            message="Kubernetes configuration could not be found.",
            guidance=[
                "Verify the KUBECONFIG_PATH setting.",
                "Confirm the backend can read the kubeconfig file.",
                "Run 'kubectl config get-contexts' on the backend machine.",
            ],
        )
    if any(
        signal in lowered
        for signal in (
            "i/o timeout",
            "context deadline exceeded",
            "timed out",
            "timeout",
        )
    ):
        return ClusterAccessError(
            code="cluster_timeout",
            message="The Kubernetes cluster did not respond in time.",
            guidance=[
                "Check your network or VPN connection.",
                "Verify the cluster API server is running.",
                "Try 'kubectl cluster-info' for the selected context.",
            ],
            status_code=504,
        )
    if any(
        signal in lowered
        for signal in (
            "connection refused",
            "unable to connect",
            "dial tcp",
            "no such host",
            "tls handshake timeout",
        )
    ):
        return ClusterAccessError(
            code="cluster_unreachable",
            message="Unable to connect to the selected Kubernetes cluster.",
            guidance=[
                "Verify the kubeconfig path and selected context.",
                "Check cluster access and your network or VPN connection.",
                "Confirm your kubectl permissions.",
            ],
        )
    if any(
        signal in lowered
        for signal in (
            "unauthorized",
            "forbidden",
            "the server has asked for the client to provide credentials",
            "you must be logged in",
            "executable aws not found",
        )
    ):
        return ClusterAccessError(
            code="cluster_access_denied",
            message="Kubernetes rejected the configured credentials or permissions.",
            guidance=[
                "Refresh the credentials in your kubeconfig file.",
                "Confirm your account can list pods, events, deployments, and services.",
            ],
            status_code=403,
        )
    return ClusterAccessError(
        code="kubectl_failed",
        message="kubectl could not read the Kubernetes configuration or cluster.",
        guidance=[
            "Run 'kubectl config get-contexts' on the backend machine.",
            "Check the backend logs for the kubectl error.",
        ],
    )


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def get_cluster_registry() -> ClusterRegistry:
    return ClusterRegistry(KubectlExecutor(kubeconfig_path=settings.kubeconfig_path))
