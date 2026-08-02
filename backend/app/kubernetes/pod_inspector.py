"""Collect pod state and identify unhealthy pods."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.kubernetes.common import object_name, object_namespace, parse_items
from app.kubernetes.kubectl_executor import KubectlExecutor


class PodInspector:
    def __init__(self, executor: KubectlExecutor, container_creating_timeout: int = 300) -> None:
        self.executor = executor
        self.container_creating_timeout = container_creating_timeout

    def inspect(self) -> dict[str, Any]:
        result = self.executor.execute("get", "pods", "-A", "-o", "json")
        pods, error = parse_items(result)
        if error:
            return {
                "healthy": False,
                "total_pods": 0,
                "problematic_pods": [],
                "error": error,
            }

        problematic = []
        for pod in pods:
            problem = self._find_problem(pod)
            if problem:
                problematic.append(problem)

        return {
            "healthy": not problematic,
            "total_pods": len(pods),
            "problematic_pods": problematic,
        }

    def _find_problem(self, pod: dict[str, Any]) -> dict[str, Any] | None:
        metadata = pod.get("metadata", {})
        status = pod.get("status", {})
        phase = str(status.get("phase", "Unknown"))
        container_statuses = [
            *status.get("initContainerStatuses", []),
            *status.get("containerStatuses", []),
        ]

        reasons: list[tuple[int, str, str]] = []
        restart_count = 0
        for container in container_statuses:
            restart_count += int(container.get("restartCount", 0))
            state = container.get("state", {})
            last_state = container.get("lastState", {})
            waiting = state.get("waiting", {})
            terminated = state.get("terminated", {})
            last_terminated = last_state.get("terminated", {})

            waiting_reason = str(waiting.get("reason", ""))
            if waiting_reason == "CrashLoopBackOff":
                reasons.append((0, waiting_reason, str(waiting.get("message", ""))))
            elif waiting_reason in {"ImagePullBackOff", "ErrImagePull"}:
                reasons.append((1, waiting_reason, str(waiting.get("message", ""))))
            elif waiting_reason == "ContainerCreating" and self._is_stuck(metadata):
                reasons.append((4, "ContainerCreating", str(waiting.get("message", ""))))

            terminated_states = [terminated]
            if not container.get("ready", False):
                terminated_states.append(last_terminated)
            for terminated_state in terminated_states:
                terminated_reason = str(terminated_state.get("reason", ""))
                if terminated_reason == "OOMKilled":
                    reasons.append((2, terminated_reason, str(terminated_state.get("message", ""))))
                elif terminated_reason == "Error":
                    reasons.append((3, terminated_reason, str(terminated_state.get("message", ""))))

        if phase == "Pending":
            reasons.append((5, "Pending", str(status.get("message", ""))))
        elif phase in {"Failed", "Error", "Unknown"}:
            reasons.append((3, "Error" if phase == "Failed" else phase, str(status.get("message", ""))))

        if not reasons:
            return None

        _, reason, message = min(reasons, key=lambda finding: finding[0])
        problem: dict[str, Any] = {
            "name": object_name(pod),
            "namespace": object_namespace(pod),
            "status": reason,
            "phase": phase,
            "restart_count": restart_count,
        }
        if message:
            problem["message"] = message
        return problem

    def _is_stuck(self, metadata: dict[str, Any]) -> bool:
        created_at = metadata.get("creationTimestamp")
        if not created_at:
            return True
        try:
            created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except ValueError:
            return True
        age = datetime.now(timezone.utc) - created.astimezone(timezone.utc)
        return age.total_seconds() >= self.container_creating_timeout
