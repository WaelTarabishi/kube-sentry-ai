import json

from app.kubernetes.kubectl_executor import KubectlResult
from app.services.investigation_service import InvestigationService


class FakeKubectlExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def execute(self, *arguments: str) -> KubectlResult:
        self.calls.append(arguments)
        resource = arguments[1] if len(arguments) > 1 else ""

        if arguments[0] == "logs":
            output = (
                "2026-08-02T12:00:00Z Exception: connection refused"
                if "--previous" not in arguments
                else "2026-08-02T11:59:00Z application startup failed"
            )
            return KubectlResult(["kubectl", *arguments], True, stdout=output, return_code=0)

        payloads = {
            "pods": {
                "items": [
                    {
                        "metadata": {
                            "name": "payment-service-abc",
                            "namespace": "default",
                            "creationTimestamp": "2026-08-02T10:00:00Z",
                            "labels": {"app": "payment-service"},
                        },
                        "status": {
                            "phase": "Running",
                            "containerStatuses": [
                                {
                                    "restartCount": 5,
                                    "state": {
                                        "waiting": {"reason": "CrashLoopBackOff"}
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "metadata": {
                            "name": "coredns-abc",
                            "namespace": "kube-system",
                            "labels": {"k8s-app": "kube-dns"},
                        },
                        "status": {"phase": "Running", "containerStatuses": []},
                    },
                ]
            },
            "events": {
                "items": [
                    {
                        "metadata": {"namespace": "default"},
                        "reason": "FailedScheduling",
                        "message": "0/1 nodes are available",
                        "count": 2,
                        "lastTimestamp": "2026-08-02T12:00:00Z",
                        "involvedObject": {"kind": "Pod", "name": "payment-service-abc"},
                    },
                    {"reason": "Pulled", "message": "Image pulled"},
                ]
            },
            "deployments": {
                "items": [
                    {
                        "metadata": {
                            "name": "payment-service",
                            "namespace": "default",
                            "generation": 2,
                        },
                        "spec": {"replicas": 2},
                        "status": {
                            "availableReplicas": 0,
                            "unavailableReplicas": 2,
                            "updatedReplicas": 1,
                            "observedGeneration": 2,
                            "conditions": [
                                {
                                    "type": "Progressing",
                                    "status": "False",
                                    "reason": "ProgressDeadlineExceeded",
                                    "message": "ReplicaSet timed out",
                                }
                            ],
                        },
                    }
                ]
            },
            "services": {
                "items": [
                    {
                        "metadata": {"name": "payment", "namespace": "default"},
                        "spec": {
                            "type": "ClusterIP",
                            "selector": {"app": "payment-service"},
                        },
                    },
                    {
                        "metadata": {"name": "kube-dns", "namespace": "kube-system"},
                        "spec": {
                            "type": "ClusterIP",
                            "selector": {"k8s-app": "kube-dns"},
                        },
                    },
                ]
            },
            "endpoints": {
                "items": [
                    {"metadata": {"name": "payment", "namespace": "default"}},
                    {
                        "metadata": {"name": "kube-dns", "namespace": "kube-system"},
                        "subsets": [{"addresses": [{"ip": "10.0.0.10"}]}],
                    },
                ]
            },
        }
        return KubectlResult(
            ["kubectl", *arguments],
            True,
            stdout=json.dumps(payloads[resource]),
            return_code=0,
        )


def test_investigation_collects_structured_evidence() -> None:
    executor = FakeKubectlExecutor()
    investigation = InvestigationService(executor).investigate()

    assert list(investigation) == ["pods", "logs", "events", "deployments", "network"]
    assert investigation["pods"]["healthy"] is False
    assert investigation["pods"]["problematic_pods"][0]["status"] == "CrashLoopBackOff"
    assert investigation["logs"]["collected_pods"] == 1
    assert investigation["logs"]["pods"][0]["matched_signals"] == [
        "connection_failures",
        "exceptions",
        "startup_errors",
    ]
    assert investigation["events"]["summary"] == {"FailedScheduling": 1}
    assert investigation["deployments"]["unhealthy_deployments"][0][
        "available_replicas"
    ] == 0
    assert investigation["network"]["problems"][0]["issue"] == (
        "Service has no ready endpoints."
    )

    commands = [(call[0], call[1]) for call in executor.calls if len(call) > 1]
    assert commands.index(("get", "pods")) < commands.index(("logs", "payment-service-abc"))
    assert commands.index(("logs", "payment-service-abc")) < commands.index(("get", "events"))
    assert commands.index(("get", "events")) < commands.index(("get", "deployments"))
    assert commands.index(("get", "deployments")) < commands.index(("get", "services"))


def test_investigation_keeps_other_sections_when_kubectl_fails() -> None:
    class FailingExecutor:
        def execute(self, *arguments: str) -> KubectlResult:
            return KubectlResult(
                ["kubectl", *arguments], False, stderr="cluster unavailable", return_code=1
            )

    investigation = InvestigationService(FailingExecutor()).investigate()

    assert investigation["pods"]["error"] == "cluster unavailable"
    assert investigation["events"]["error"] == "cluster unavailable"
    assert investigation["deployments"]["error"] == "cluster unavailable"
    assert investigation["network"]["errors"] == [
        "cluster unavailable",
        "cluster unavailable",
        "cluster unavailable",
    ]
