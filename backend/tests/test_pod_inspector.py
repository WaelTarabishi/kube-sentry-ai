import json

import pytest

from app.kubernetes.kubectl_executor import KubectlResult
from app.kubernetes.pod_inspector import PodInspector


class PodExecutor:
    def __init__(self, pod: dict) -> None:
        self.pod = pod

    def execute(self, *_arguments: str) -> KubectlResult:
        return KubectlResult(
            command=["kubectl", "get", "pods"],
            success=True,
            stdout=json.dumps({"items": [self.pod]}),
            return_code=0,
        )


@pytest.mark.parametrize(
    ("phase", "state", "expected"),
    [
        ("Running", {"waiting": {"reason": "CrashLoopBackOff"}}, "CrashLoopBackOff"),
        ("Pending", {"waiting": {"reason": "ImagePullBackOff"}}, "ImagePullBackOff"),
        ("Pending", {}, "Pending"),
        ("Failed", {"terminated": {"reason": "Error"}}, "Error"),
        ("Running", {"terminated": {"reason": "OOMKilled"}}, "OOMKilled"),
        ("Pending", {"waiting": {"reason": "ContainerCreating"}}, "ContainerCreating"),
    ],
)
def test_detects_problematic_pod_states(phase: str, state: dict, expected: str) -> None:
    pod = {
        "metadata": {
            "name": "broken-pod",
            "namespace": "default",
            "creationTimestamp": "2020-01-01T00:00:00Z",
        },
        "status": {
            "phase": phase,
            "containerStatuses": [{"restartCount": 1, "ready": False, "state": state}],
        },
    }

    result = PodInspector(PodExecutor(pod)).inspect()

    assert result["healthy"] is False
    assert result["problematic_pods"][0]["status"] == expected


def test_ignores_old_oomkill_for_a_recovered_container() -> None:
    pod = {
        "metadata": {"name": "recovered", "namespace": "default"},
        "status": {
            "phase": "Running",
            "containerStatuses": [
                {
                    "restartCount": 1,
                    "ready": True,
                    "state": {"running": {}},
                    "lastState": {"terminated": {"reason": "OOMKilled"}},
                }
            ],
        },
    }

    result = PodInspector(PodExecutor(pod)).inspect()

    assert result["healthy"] is True
    assert result["problematic_pods"] == []
