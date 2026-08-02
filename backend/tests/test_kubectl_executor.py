import subprocess

from app.kubernetes.kubectl_executor import KubectlExecutor


def test_executor_returns_structured_output(monkeypatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="pods-json\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = KubectlExecutor(kubeconfig_path="cluster.yaml").execute("get", "pods", "-A")

    assert result.success is True
    assert result.stdout == "pods-json"
    assert result.return_code == 0
    assert captured["command"] == ["kubectl", "get", "pods", "-A"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["env"]["KUBECONFIG"] == "cluster.yaml"


def test_executor_handles_missing_kubectl(monkeypatch) -> None:
    def missing_command(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing_command)
    result = KubectlExecutor().execute("get", "pods")

    assert result.success is False
    assert result.return_code is None
    assert "was not found" in result.stderr
