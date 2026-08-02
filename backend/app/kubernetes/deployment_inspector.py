"""Inspect deployment replica counts and rollout conditions."""

from __future__ import annotations

from typing import Any

from app.kubernetes.common import object_name, object_namespace, parse_items
from app.kubernetes.kubectl_executor import KubectlExecutor


class DeploymentInspector:
    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self) -> dict[str, Any]:
        result = self.executor.execute("get", "deployments", "-A", "-o", "json")
        deployments, error = parse_items(result)
        if error:
            return {
                "healthy": False,
                "total_deployments": 0,
                "unhealthy_deployments": [],
                "error": error,
            }

        unhealthy = []
        for deployment in deployments:
            finding = self._inspect_deployment(deployment)
            if finding:
                unhealthy.append(finding)

        return {
            "healthy": not unhealthy,
            "total_deployments": len(deployments),
            "unhealthy_deployments": unhealthy,
        }

    @staticmethod
    def _inspect_deployment(deployment: dict[str, Any]) -> dict[str, Any] | None:
        metadata = deployment.get("metadata", {})
        spec = deployment.get("spec", {})
        status = deployment.get("status", {})
        desired = int(spec.get("replicas", 1))
        available = int(status.get("availableReplicas", 0))
        unavailable = int(status.get("unavailableReplicas", max(desired - available, 0)))
        updated = int(status.get("updatedReplicas", 0))
        issues = []

        if available < desired:
            issues.append("Available replicas are below the desired count.")
        if unavailable > 0:
            issues.append("One or more replicas are unavailable.")
        if int(status.get("observedGeneration", 0)) < int(metadata.get("generation", 0)):
            issues.append("The latest deployment generation has not been observed.")

        condition_findings = []
        for condition in status.get("conditions", []):
            condition_type = str(condition.get("type", "Unknown"))
            condition_status = str(condition.get("status", "Unknown"))
            is_failure = (
                condition_type in {"Available", "Progressing"} and condition_status == "False"
            ) or (condition_type == "ReplicaFailure" and condition_status == "True")
            if is_failure:
                condition_findings.append(
                    {
                        "type": condition_type,
                        "status": condition_status,
                        "reason": condition.get("reason", ""),
                        "message": condition.get("message", ""),
                    }
                )

        if condition_findings:
            issues.append("Deployment conditions report a rollout failure.")
        if not issues:
            return None

        return {
            "name": object_name(deployment),
            "namespace": object_namespace(deployment),
            "desired_replicas": desired,
            "available_replicas": available,
            "unavailable_replicas": unavailable,
            "updated_replicas": updated,
            "issues": issues,
            "conditions": condition_findings,
        }
