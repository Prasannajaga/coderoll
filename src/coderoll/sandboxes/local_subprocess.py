from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from ..candidate import Candidate
from ..errors import SandboxError, TaskError
from ..result import ExecutionResult
from ..task import Task
from .docker_cli import _should_skip, _to_text


class LocalSubprocessSandbox:
    """Unsafe local execution sandbox for trusted debugging only."""

    def __init__(self, timeout: int = 5, keep_workspace: bool = False) -> None:
        self.timeout = timeout
        self.keep_workspace = keep_workspace

    def run(self, task: Task, candidate: Candidate) -> ExecutionResult:
        if not task.test_path.exists():
            raise TaskError(f"Task test file does not exist: {task.test_path}")

        workspace = Path(tempfile.mkdtemp(prefix="coderoll_local_"))
        sandbox_meta: dict[str, object] = {
            "type": "local_subprocess",
            "unsafe": True,
            "timeout": self.timeout,
        }
        if self.keep_workspace:
            sandbox_meta["workspace"] = str(workspace)

        try:
            for source in task.root.rglob("*"):
                if source.is_dir():
                    continue
                relative = source.relative_to(task.root)
                if _should_skip(relative):
                    continue
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            entry_path = workspace / task.entry_file
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            entry_path.write_text(candidate.code or "", encoding="utf-8")

            test_target = workspace / task.test_file
            test_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(task.test_path, test_target)

            started = time.time()
            try:
                completed = subprocess.run(
                    ["sh", "-c", task.test_command],
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=self.timeout + 2,
                )
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
                    language=task.language,
                    image=task.image,
                    phase="timeout",
                    test_exit_code=None,
                    test_stdout=_to_text(exc.stdout),
                    test_stderr=_to_text(exc.stderr),
                )
            except OSError as exc:
                raise SandboxError(f"Failed to run local subprocess sandbox: {exc}") from exc

            duration_ms = int((time.time() - started) * 1000)
            return ExecutionResult(
                task_id=task.id,
                candidate_id=candidate.id,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_ms=duration_ms,
                timed_out=False,
                error=None,
                sandbox=sandbox_meta,
                language=task.language,
                image=task.image,
                phase="test",
                test_exit_code=completed.returncode,
                test_stdout=completed.stdout,
                test_stderr=completed.stderr,
            )
        finally:
            if not self.keep_workspace:
                shutil.rmtree(workspace, ignore_errors=True)
