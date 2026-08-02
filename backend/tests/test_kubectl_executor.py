import subprocess

from app.kubernetes.kubectl_executor import KubectlExecutor


def test_executor_returns_structured_output(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="pods-json\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    kubeconfig = tmp_path / "cluster.yaml"
    kubeconfig.write_text("apiVersion: v1", encoding="utf-8")
    result = KubectlExecutor(kubeconfig_path=str(kubeconfig)).execute("get", "pods", "-A")

    assert result.success is True
    assert result.stdout == "pods-json"
    assert result.return_code == 0
    assert captured["command"] == ["kubectl", "get", "pods", "-A"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["env"]["KUBECONFIG"] == str(kubeconfig)


def test_executor_applies_selected_context(monkeypatch) -> None:
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = KubectlExecutor(context="kind-development").execute("get", "pods", "-A")

    assert result.success is True
    assert captured["command"] == [
        "kubectl",
        "--context",
        "kind-development",
        "get",
        "pods",
        "-A",
    ]


def test_executor_reports_missing_explicit_kubeconfig(tmp_path) -> None:
    result = KubectlExecutor(kubeconfig_path=str(tmp_path / "missing.yaml")).execute(
        "config", "view"
    )

    assert result.success is False
    assert "Kubeconfig file was not found" in result.stderr


def test_executor_handles_missing_kubectl(monkeypatch) -> None:
    def missing_command(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", missing_command)
    result = KubectlExecutor().execute("get", "pods")

    assert result.success is False
    assert result.return_code is None
    assert "was not found" in result.stderr
