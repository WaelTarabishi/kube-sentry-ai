"""Shared helpers for parsing kubectl JSON output."""

from __future__ import annotations

import json
from typing import Any

from app.kubernetes.kubectl_executor import KubectlResult


def parse_items(result: KubectlResult) -> tuple[list[dict[str, Any]], str | None]:
    if not result.success:
        return [], result.stderr or "kubectl command failed."

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [], f"kubectl returned invalid JSON: {exc.msg}."

    items = payload.get("items")
    if not isinstance(items, list):
        return [], "kubectl JSON did not contain an items list."
    return [item for item in items if isinstance(item, dict)], None


def object_name(item: dict[str, Any]) -> str:
    return str(item.get("metadata", {}).get("name", "unknown"))


def object_namespace(item: dict[str, Any]) -> str:
    return str(item.get("metadata", {}).get("namespace", "default"))
