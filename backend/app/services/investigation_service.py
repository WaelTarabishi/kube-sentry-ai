"""Orchestrate all Kubernetes evidence collectors in a predictable order."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger

from app.core.config import settings
from app.kubernetes.deployment_inspector import DeploymentInspector
from app.kubernetes.events_analyzer import EventsAnalyzer
from app.kubernetes.kubectl_executor import KubectlExecutor
from app.kubernetes.logs_collector import LogsCollector
from app.kubernetes.network_inspector import NetworkInspector
from app.kubernetes.pod_inspector import PodInspector


class InvestigationService:
    def __init__(self, executor: KubectlExecutor | None = None) -> None:
        executor = executor or KubectlExecutor(kubeconfig_path=settings.kubeconfig_path)
        self.pod_inspector = PodInspector(executor)
        self.logs_collector = LogsCollector(executor)
        self.events_analyzer = EventsAnalyzer(executor)
        self.deployment_inspector = DeploymentInspector(executor)
        self.network_inspector = NetworkInspector(executor)

    def investigate(self) -> dict[str, dict[str, Any]]:
        """Run each evidence collector and keep partial results on failure."""

        pods = self._run_step("pods", self.pod_inspector.inspect)
        problematic_pods = pods.get("problematic_pods", [])
        if not isinstance(problematic_pods, list):
            problematic_pods = []

        logs = self._run_step(
            "logs", lambda: self.logs_collector.collect(problematic_pods)
        )
        events = self._run_step("events", self.events_analyzer.analyze)
        deployments = self._run_step("deployments", self.deployment_inspector.inspect)
        network = self._run_step("network", lambda: self.network_inspector.inspect(logs))

        return {
            "pods": pods,
            "logs": logs,
            "events": events,
            "deployments": deployments,
            "network": network,
        }

    @staticmethod
    def _run_step(
        name: str, operation: Callable[[], dict[str, Any]]
    ) -> dict[str, Any]:
        logger.info("Starting Kubernetes investigation step: {}", name)
        try:
            return operation()
        except Exception as exc:  # Keeps independent evidence available if one collector fails.
            logger.exception("Kubernetes investigation step '{}' failed", name)
            return {"healthy": False, "error": f"{name} inspection failed: {exc}"}


def get_investigation_service() -> InvestigationService:
    """FastAPI dependency factory, kept separate to make the endpoint testable."""

    return InvestigationService()
