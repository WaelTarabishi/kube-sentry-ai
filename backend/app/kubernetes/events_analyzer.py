"""Summarize Kubernetes warning events that commonly explain failures."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.kubernetes.common import object_name, object_namespace, parse_items
from app.kubernetes.kubectl_executor import KubectlExecutor


IMPORTANT_REASONS = {
    "FailedScheduling",
    "BackOff",
    "FailedMount",
    "FailedPull",
    "ErrImagePull",
    "Unhealthy",
}


class EventsAnalyzer:
    def __init__(self, executor: KubectlExecutor, max_events: int = 100) -> None:
        self.executor = executor
        self.max_events = max_events

    def analyze(self) -> dict[str, Any]:
        result = self.executor.execute("get", "events", "-A", "-o", "json")
        events, error = parse_items(result)
        if error:
            return {"healthy": False, "findings": [], "summary": {}, "error": error}

        relevant = [event for event in events if event.get("reason") in IMPORTANT_REASONS]
        relevant.sort(key=_event_time, reverse=True)
        relevant = relevant[: self.max_events]
        summary = Counter(str(event.get("reason")) for event in relevant)

        findings = []
        for event in relevant:
            involved = event.get("involvedObject", {})
            findings.append(
                {
                    "reason": event.get("reason", "Unknown"),
                    "namespace": object_namespace(event),
                    "object": {
                        "kind": involved.get("kind", "Unknown"),
                        "name": involved.get("name", object_name(event)),
                    },
                    "message": event.get("message", ""),
                    "count": event.get("count", 1),
                    "last_seen": _event_time(event),
                }
            )

        return {
            "healthy": not findings,
            "findings": findings,
            "summary": dict(sorted(summary.items())),
        }


def _event_time(event: dict[str, Any]) -> str:
    return str(
        event.get("eventTime")
        or event.get("lastTimestamp")
        or event.get("metadata", {}).get("creationTimestamp")
        or ""
    )
