from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

from ..candidate import Candidate
from ..errors import DockerError, TaskError
from ..result import ExecutionResult
from ..task import Task


EXCLUDED_FILENAMES = {"task.toml", "prompt.txt", "candidates.jsonl"}


class DockerSandbox:
    def __init__(
        self,
        image: str = "coderoll-python:3.11",
        timeout: int = 5,
        memory: str = "256m",
        cpus: str = "1",
        pids_limit: int = 128,
        network: bool = False,
        keep_workspace: bool = False,
    ) -> None:
        self.image = image
        self.timeout = timeout
        self.memory = memory
        self.cpus = cpus
        self.pids_limit = pids_limit
        self.network = network
        self.keep_workspace = keep_workspace

    def run(self, task: Task, candidate: Candidate) -> ExecutionResult:
        if not task.test_path.exists():
            raise TaskError(f"Task test file does not exist: {task.test_path}")

        workspace = Path(tempfile.mkdtemp(prefix="coderoll_"))
        sandbox_meta = self._sandbox_meta(workspace)

        try:
            self._copy_support_files(task.root, workspace)

            entry_path = workspace / task.entry_file
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            entry_path.write_text(candidate.code, encoding="utf-8")

            test_target = workspace / task.test_file
            test_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(task.test_path, test_target)

            command = [
                "docker",
                "run",
                "--rm",
                "--memory",
                self.memory,
                "--cpus",
                self.cpus,
                "--pids-limit",
                str(self.pids_limit),
                "-v",
                f"{workspace}:/workspace",
                "-w",
                "/workspace",
            ]
            if not self.network:
                command.extend(["--network", "none"])
            command.extend([self.image, "sh", "-c", task.test_command])

            started = time.time()
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=self.timeout + 2,
                )
            except FileNotFoundError as exc:
                raise DockerError(
                    "Docker CLI was not found. Install Docker and ensure `docker` is available on PATH."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                duration_ms = int((time.time() - started) * 1000)
                return ExecutionResult(
                    task_id=task.id,
                    candidate_id=candidate.id,
                    exit_code=-1,
                    stdout=_to_text(exc.stdout),
                    stderr=_to_text(exc.stderr),
                    duration_ms=duration_ms,
                    timed_out=True,
                    error=f"Execution timed out after {self.timeout} seconds.",
                    sandbox=sandbox_meta,
                )

            duration_ms = int((time.time() - started) * 1000)
            error: str | None = None
            if completed.returncode == 125 and _looks_like_missing_image(completed.stderr):
                error = (
                    f"Docker image '{self.image}' was not found. "
                    "Run `coderoll build-image` before running evaluations."
                )

            return ExecutionResult(
                task_id=task.id,
                candidate_id=candidate.id,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_ms=duration_ms,
                timed_out=False,
                error=error,
                sandbox=sandbox_meta,
            )
        finally:
            if not self.keep_workspace:
                shutil.rmtree(workspace, ignore_errors=True)

    def _copy_support_files(self, task_root: Path, workspace: Path) -> None:
        for source in task_root.rglob("*"):
            if source.is_dir():
                continue
            relative = source.relative_to(task_root)
            if _should_skip(relative):
                continue

            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def _sandbox_meta(self, workspace: Path) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "type": "docker_cli",
            "image": self.image,
            "timeout": self.timeout,
            "memory": self.memory,
            "cpus": self.cpus,
            "pids_limit": self.pids_limit,
            "network": self.network,
        }
        if self.keep_workspace:
            meta["workspace"] = str(workspace)
        return meta


def _should_skip(relative: Path) -> bool:
    if any(part == "__pycache__" for part in relative.parts):
        return True
    if any(part.startswith(".") for part in relative.parts):
        return True
    if len(relative.parts) == 1 and relative.name in EXCLUDED_FILENAMES:
        return True
    return False


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _looks_like_missing_image(stderr: str) -> bool:
    text = stderr.lower()
    return "unable to find image" in text or "pull access denied" in text
