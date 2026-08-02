"""Small, safe wrapper around the ``kubectl`` command line tool."""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass

from loguru import logger


@dataclass(slots=True)
class KubectlResult:
    """Structured result returned for every kubectl invocation."""

    command: list[str]
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class KubectlExecutor:
    """Execute kubectl without a shell and turn failures into data."""

    def __init__(
        self,
        kubeconfig_path: str = "",
        timeout_seconds: int = 30,
        executable: str = "kubectl",
    ) -> None:
        self.kubeconfig_path = kubeconfig_path
        self.timeout_seconds = timeout_seconds
        self.executable = executable

    def execute(self, *arguments: str) -> KubectlResult:
        if not arguments or any(not isinstance(arg, str) or "\x00" in arg for arg in arguments):
            return KubectlResult(
                command=[self.executable],
                success=False,
                stderr="Invalid kubectl arguments.",
            )

        command = [self.executable, *arguments]
        environment = os.environ.copy()
        if self.kubeconfig_path:
            environment["KUBECONFIG"] = self.kubeconfig_path

        logger.info("Running kubectl command: {}", " ".join(command))
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                env=environment,
                shell=False,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            message = f"kubectl executable '{self.executable}' was not found."
            logger.error(message)
            return KubectlResult(command=command, success=False, stderr=message)
        except subprocess.TimeoutExpired as exc:
            message = f"kubectl command timed out after {self.timeout_seconds} seconds."
            logger.warning("{} Command: {}", message, " ".join(command))
            return KubectlResult(
                command=command,
                success=False,
                stdout=_to_text(exc.stdout),
                stderr=message,
            )
        except OSError as exc:
            message = f"Unable to run kubectl: {exc}"
            logger.exception(message)
            return KubectlResult(command=command, success=False, stderr=message)

        success = completed.returncode == 0
        if not success:
            logger.warning(
                "kubectl exited with code {}: {}",
                completed.returncode,
                completed.stderr.strip(),
            )

        return KubectlResult(
            command=command,
            success=success,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
            return_code=completed.returncode,
        )


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value
