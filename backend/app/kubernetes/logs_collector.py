"""Collect a concise set of useful log lines from unhealthy pods."""

from __future__ import annotations

import re
from typing import Any

from app.kubernetes.kubectl_executor import KubectlExecutor


SIGNAL_PATTERNS = {
    "exceptions": re.compile(r"exception|traceback|panic|fatal", re.IGNORECASE),
    "connection_failures": re.compile(
        r"connection (?:refused|reset|timed out)|no route to host|dial tcp|connect timeout",
        re.IGNORECASE,
    ),
    "missing_environment_variables": re.compile(
        r"(?:environment|env) variable.*(?:missing|not set|required)|missing.*(?:environment|env) variable",
        re.IGNORECASE,
    ),
    "image_failures": re.compile(
        r"failed to pull image|imagepull|errimagepull|manifest unknown", re.IGNORECASE
    ),
    "startup_errors": re.compile(
        r"failed to start|startup .*failed|address already in use|permission denied",
        re.IGNORECASE,
    ),
    "dns": re.compile(
        r"no such host|name or service not known|temporary failure in name resolution|dns lookup",
        re.IGNORECASE,
    ),
}


class LogsCollector:
    def __init__(self, executor: KubectlExecutor, tail_lines: int = 100, max_lines: int = 40) -> None:
        self.executor = executor
        self.tail_lines = tail_lines
        self.max_lines = max_lines

    def collect(self, problematic_pods: list[dict[str, Any]]) -> dict[str, Any]:
        collected = [self._collect_pod(pod) for pod in problematic_pods]
        return {"collected_pods": len(collected), "pods": collected}

    def _collect_pod(self, pod: dict[str, Any]) -> dict[str, Any]:
        name = str(pod["name"])
        namespace = str(pod["namespace"])
        current = self.executor.execute(
            "logs",
            name,
            "-n",
            namespace,
            "--all-containers=true",
            f"--tail={self.tail_lines}",
            "--timestamps=true",
        )

        outputs = [current.stdout] if current.success else []
        errors = [current.stderr] if not current.success and current.stderr else []

        if pod.get("status") in {"CrashLoopBackOff", "OOMKilled", "Error"}:
            previous = self.executor.execute(
                "logs",
                name,
                "-n",
                namespace,
                "--all-containers=true",
                "--previous",
                f"--tail={self.tail_lines}",
                "--timestamps=true",
            )
            if previous.success:
                outputs.append(previous.stdout)
            elif previous.stderr:
                errors.append(previous.stderr)

        # kubectl reports image/startup failures on stderr when a container never started.
        lines = _unique_lines("\n".join([*outputs, *errors]))
        matched_signals: set[str] = set()
        relevant_lines = []
        for line in lines:
            line_signals = [name for name, pattern in SIGNAL_PATTERNS.items() if pattern.search(line)]
            if line_signals:
                matched_signals.update(line_signals)
                relevant_lines.append(line)

        if not relevant_lines:
            relevant_lines = lines[-min(20, self.max_lines) :]

        evidence: dict[str, Any] = {
            "name": name,
            "namespace": namespace,
            "pod_status": pod.get("status", "Unknown"),
            "matched_signals": sorted(matched_signals),
            "lines": relevant_lines[-self.max_lines :],
        }
        if errors and not outputs:
            evidence["error"] = "; ".join(errors)
        return evidence


def _unique_lines(output: str) -> list[str]:
    lines = []
    seen = set()
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return lines
