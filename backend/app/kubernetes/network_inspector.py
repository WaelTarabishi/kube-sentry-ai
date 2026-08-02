"""Inspect services, selectors, endpoints, and basic cluster DNS signals."""

from __future__ import annotations

from typing import Any

from app.kubernetes.common import object_name, object_namespace, parse_items
from app.kubernetes.kubectl_executor import KubectlExecutor


class NetworkInspector:
    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self, logs: dict[str, Any] | None = None) -> dict[str, Any]:
        services, services_error = parse_items(
            self.executor.execute("get", "services", "-A", "-o", "json")
        )
        endpoints, endpoints_error = parse_items(
            self.executor.execute("get", "endpoints", "-A", "-o", "json")
        )
        pods, pods_error = parse_items(
            self.executor.execute("get", "pods", "-A", "-o", "json")
        )

        errors = [error for error in (services_error, endpoints_error, pods_error) if error]
        endpoint_map = {
            (object_namespace(endpoint), object_name(endpoint)): endpoint for endpoint in endpoints
        }
        problems = []
        service_summaries = []

        if not services and not services_error:
            problems.append({"issue": "No services were found in the cluster."})

        for service in services:
            namespace = object_namespace(service)
            name = object_name(service)
            spec = service.get("spec", {})
            selector = spec.get("selector") or {}
            service_type = spec.get("type", "ClusterIP")
            endpoint = endpoint_map.get((namespace, name), {})
            ready_addresses = sum(
                len(subset.get("addresses", [])) for subset in endpoint.get("subsets", [])
            )
            matching_pods = _matching_pods(pods, namespace, selector) if selector else []

            service_summaries.append(
                {
                    "name": name,
                    "namespace": namespace,
                    "type": service_type,
                    "ready_endpoints": ready_addresses,
                }
            )

            if service_type == "ExternalName" or not selector:
                continue
            if not matching_pods:
                problems.append(
                    {
                        "service": name,
                        "namespace": namespace,
                        "issue": "Selector does not match any pods.",
                        "selector": selector,
                    }
                )
            elif ready_addresses == 0:
                problems.append(
                    {
                        "service": name,
                        "namespace": namespace,
                        "issue": "Service has no ready endpoints.",
                        "matching_pods": len(matching_pods),
                    }
                )

        dns_issues = _dns_log_issues(logs or {})
        dns_services = [
            summary
            for summary in service_summaries
            if summary["namespace"] == "kube-system"
            and summary["name"] in {"kube-dns", "coredns"}
        ]
        if services and not dns_services:
            dns_issues.append("No kube-dns or coredns service was found in kube-system.")
        elif dns_services and all(service["ready_endpoints"] == 0 for service in dns_services):
            dns_issues.append("The cluster DNS service has no ready endpoints.")

        return {
            "healthy": not problems and not dns_issues and not errors,
            "total_services": len(services),
            "services": service_summaries,
            "problems": problems,
            "dns_issues": dns_issues,
            **({"errors": errors} if errors else {}),
        }


def _matching_pods(
    pods: list[dict[str, Any]], namespace: str, selector: dict[str, str]
) -> list[dict[str, Any]]:
    return [
        pod
        for pod in pods
        if object_namespace(pod) == namespace
        and all(pod.get("metadata", {}).get("labels", {}).get(key) == value for key, value in selector.items())
    ]


def _dns_log_issues(logs: dict[str, Any]) -> list[str]:
    issues = []
    for pod in logs.get("pods", []):
        if "dns" in pod.get("matched_signals", []):
            issues.append(
                f"DNS failure text was found in logs for {pod.get('namespace')}/{pod.get('name')}."
            )
    return issues
