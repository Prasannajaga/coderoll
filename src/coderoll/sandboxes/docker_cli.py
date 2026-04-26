from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

from ..candidate import Candidate
from ..errors import DockerError, TaskError
from ..parsers import parse_junit_xml, parse_tap_output
from ..result import CommandResult, ExecutionResult
from ..task import Task


EXCLUDED_FILENAMES = {"task.toml", "prompt.txt", "candidates.jsonl"}


class DockerSandbox:
    def __init__(
        self,
        image: str | None = None,
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
        image = self.image or task.image
        if not image:
            raise TaskError(f"No Docker image configured for task language: {task.language}")
        sandbox_meta = self._sandbox_meta(workspace, image)

        try:
            self._copy_support_files(task.root, workspace, skip_relpaths={task.test_file})

            entry_path = workspace / task.entry_file
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            entry_path.write_text(candidate.code or "", encoding="utf-8")

            test_target = workspace / task.test_file
            test_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(task.test_path, test_target)

            total_started = time.time()
            build_stdout = ""
            build_stderr = ""
            build_exit_code: int | None = None
            if task.build_command:
                build = self._run_docker_command(workspace, image, task.build_command)
                build_stdout = build["stdout"]
                build_stderr = build["stderr"]
                build_exit_code = build["exit_code"]
                if build["timed_out"]:
                    duration_ms = int((time.time() - total_started) * 1000)
                    return self._execution_result(
                        task=task,
                        candidate=candidate,
                        image=image,
                        sandbox_meta=sandbox_meta,
                        phase="timeout",
                        exit_code=-1,
                        duration_ms=duration_ms,
                        timed_out=True,
                        error=f"Build timed out after {self.timeout} seconds.",
                        build_exit_code=None,
                        build_stdout=build_stdout,
                        build_stderr=build_stderr,
                    )
                build_error = _docker_error(image, build_stderr, build_exit_code)
                if build_exit_code != 0:
                    duration_ms = int((time.time() - total_started) * 1000)
                    return self._execution_result(
                        task=task,
                        candidate=candidate,
                        image=image,
                        sandbox_meta=sandbox_meta,
                        phase="build",
                        exit_code=build_exit_code,
                        duration_ms=duration_ms,
                        timed_out=False,
                        error=build_error,
                        build_exit_code=build_exit_code,
                        build_stdout=build_stdout,
                        build_stderr=build_stderr,
                    )

            test = self._run_docker_command(workspace, image, task.test_command)
            duration_ms = int((time.time() - total_started) * 1000)
            tests = self._parse_results(task.result_format, workspace, test["stdout"])
            if test["timed_out"]:
                return ExecutionResult(
                    task_id=task.id,
                    candidate_id=candidate.id,
                    exit_code=-1,
                    stdout=_combine_outputs(build_stdout, build_stderr, test["stdout"], test["stderr"]),
                    stderr=_combine_errors(build_stderr, test["stderr"]),
                    duration_ms=duration_ms,
                    timed_out=True,
                    error=f"Execution timed out after {self.timeout} seconds.",
                    sandbox=sandbox_meta,
                    language=task.language,
                    image=image,
                    phase="timeout",
                    build_exit_code=build_exit_code,
                    build_stdout=build_stdout,
                    build_stderr=build_stderr,
                    test_exit_code=None,
                    test_stdout=test["stdout"],
                    test_stderr=test["stderr"],
                    **tests,
                )

            error = _docker_error(image, test["stderr"], test["exit_code"])

            return ExecutionResult(
                task_id=task.id,
                candidate_id=candidate.id,
                exit_code=test["exit_code"],
                stdout=_combine_outputs(build_stdout, build_stderr, test["stdout"], test["stderr"]),
                stderr=_combine_errors(build_stderr, test["stderr"]),
                duration_ms=duration_ms,
                timed_out=False,
                error=error,
                sandbox=sandbox_meta,
                language=task.language,
                image=image,
                phase="test" if error is None else "infra",
                build_exit_code=build_exit_code,
                build_stdout=build_stdout,
                build_stderr=build_stderr,
                test_exit_code=test["exit_code"],
                test_stdout=test["stdout"],
                test_stderr=test["stderr"],
                **tests,
            )
        finally:
            if not self.keep_workspace:
                shutil.rmtree(workspace, ignore_errors=True)

    def run_prepared_workspace(
        self,
        config_id: str,
        candidate: Candidate,
        workspace: Path,
        image: str,
        setup_commands: list[str],
        dependency_commands: list[str],
        eval_commands: list[Any],
        default_result_format: str = "exit_code",
        setup_timeout: int | None = None,
        stop_on_first_failure: bool = False,
        language: str | None = None,
    ) -> ExecutionResult:
        sandbox_meta = self._sandbox_meta(workspace, image)
        total_started = time.time()
        command_results: list[CommandResult] = []
        setup_stdout: list[str] = []
        setup_stderr: list[str] = []
        setup_duration_ms = 0

        for index, command in enumerate(setup_commands):
            result = self._run_command_result(
                workspace=workspace,
                image=image,
                command=command,
                phase="setup",
                name=f"setup_{index + 1}",
                result_format="exit_code",
                timeout=setup_timeout or self.timeout,
            )
            command_results.append(result)
            setup_stdout.append(_section(result.name or "setup", result.stdout))
            setup_stderr.append(_section(result.name or "setup", result.stderr))
            setup_duration_ms += result.duration_ms
            if result.timed_out:
                return self._prepared_result(
                    config_id,
                    candidate,
                    image,
                    sandbox_meta,
                    phase="timeout",
                    exit_code=-1,
                    error=f"Setup timed out after {setup_timeout or self.timeout} seconds.",
                    duration_ms=int((time.time() - total_started) * 1000),
                    timed_out=True,
                    command_results=command_results,
                    setup_stdout="\n".join(setup_stdout),
                    setup_stderr="\n".join(setup_stderr),
                    setup_duration_ms=setup_duration_ms,
                    setup_passed=False,
                    language=language,
                )
            if result.exit_code != 0:
                return self._prepared_result(
                    config_id,
                    candidate,
                    image,
                    sandbox_meta,
                    phase="setup",
                    exit_code=result.exit_code,
                    error=_docker_error(image, result.stderr, result.exit_code),
                    duration_ms=int((time.time() - total_started) * 1000),
                    timed_out=False,
                    command_results=command_results,
                    setup_stdout="\n".join(setup_stdout),
                    setup_stderr="\n".join(setup_stderr),
                    setup_duration_ms=setup_duration_ms,
                    setup_passed=False,
                    language=language,
                )

        for index, command in enumerate(dependency_commands):
            result = self._run_command_result(
                workspace=workspace,
                image=image,
                command=command,
                phase="setup",
                name=f"dependency_{index + 1}",
                result_format="exit_code",
                timeout=setup_timeout or self.timeout,
            )
            command_results.append(result)
            setup_stdout.append(_section(result.name or "dependency", result.stdout))
            setup_stderr.append(_section(result.name or "dependency", result.stderr))
            setup_duration_ms += result.duration_ms
            if result.timed_out or result.exit_code != 0:
                phase = "timeout" if result.timed_out else "setup"
                return self._prepared_result(
                    config_id,
                    candidate,
                    image,
                    sandbox_meta,
                    phase=phase,
                    exit_code=-1 if result.timed_out else result.exit_code,
                    error=(
                        f"Dependency setup timed out after {setup_timeout or self.timeout} seconds."
                        if result.timed_out
                        else _docker_error(image, result.stderr, result.exit_code)
                    ),
                    duration_ms=int((time.time() - total_started) * 1000),
                    timed_out=result.timed_out,
                    command_results=command_results,
                    setup_stdout="\n".join(setup_stdout),
                    setup_stderr="\n".join(setup_stderr),
                    setup_duration_ms=setup_duration_ms,
                    setup_passed=False,
                    language=language,
                )

        for index, spec in enumerate(eval_commands):
            command = getattr(spec, "command", str(spec))
            name = getattr(spec, "name", None) or f"eval_{index + 1}"
            result_format = getattr(spec, "result_format", None) or default_result_format
            result = self._run_command_result(
                workspace=workspace,
                image=image,
                command=command,
                phase="eval",
                name=name,
                result_format=result_format,
                timeout=self.timeout,
            )
            command_results.append(result)
            if result.timed_out:
                return self._prepared_result(
                    config_id,
                    candidate,
                    image,
                    sandbox_meta,
                    phase="timeout",
                    exit_code=-1,
                    error=f"Execution timed out after {self.timeout} seconds.",
                    duration_ms=int((time.time() - total_started) * 1000),
                    timed_out=True,
                    command_results=command_results,
                    setup_stdout="\n".join(setup_stdout),
                    setup_stderr="\n".join(setup_stderr),
                    setup_duration_ms=setup_duration_ms,
                    setup_passed=True,
                    language=language,
                )
            if stop_on_first_failure and result.exit_code != 0:
                break

        eval_results = [result for result in command_results if result.phase == "eval"]
        exit_code = 0 if eval_results and all(result.exit_code == 0 for result in eval_results) else 1
        phase = "complete" if exit_code == 0 else "eval"
        return self._prepared_result(
            config_id,
            candidate,
            image,
            sandbox_meta,
            phase=phase,
            exit_code=exit_code,
            error=None,
            duration_ms=int((time.time() - total_started) * 1000),
            timed_out=False,
            command_results=command_results,
            setup_stdout="\n".join(setup_stdout),
            setup_stderr="\n".join(setup_stderr),
            setup_duration_ms=setup_duration_ms,
            setup_passed=True,
            language=language,
        )

    def _run_docker_command(self, workspace: Path, image: str, shell_command: str) -> dict[str, Any]:
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
        command.extend([image, "sh", "-c", shell_command])

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
            return {
                "exit_code": -1,
                "stdout": _to_text(exc.stdout),
                "stderr": _to_text(exc.stderr),
                "timed_out": True,
            }

        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }

    def _run_command_result(
        self,
        workspace: Path,
        image: str,
        command: str,
        phase: str,
        name: str | None,
        result_format: str,
        timeout: int,
    ) -> CommandResult:
        if result_format == "junit":
            (workspace / ".coderoll-results.xml").unlink(missing_ok=True)
        started = time.time()
        raw = self._run_docker_command_with_timeout(workspace, image, command, timeout)
        duration_ms = int((time.time() - started) * 1000)
        tests = self._parse_results(result_format, workspace, raw["stdout"])
        return CommandResult(
            name=name,
            command=command,
            phase=phase,
            exit_code=raw["exit_code"],
            stdout=raw["stdout"],
            stderr=raw["stderr"],
            duration_ms=duration_ms,
            timed_out=raw["timed_out"],
            **tests,
        )

    def _run_docker_command_with_timeout(
        self,
        workspace: Path,
        image: str,
        shell_command: str,
        timeout: int,
    ) -> dict[str, Any]:
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
        command.extend([image, "sh", "-lc", shell_command])

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout + 2,
            )
        except FileNotFoundError as exc:
            raise DockerError(
                "Docker CLI was not found. Install Docker and ensure `docker` is available on PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            return {
                "exit_code": -1,
                "stdout": _to_text(exc.stdout),
                "stderr": _to_text(exc.stderr),
                "timed_out": True,
            }

        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }

    def _parse_results(
        self,
        result_format: str,
        workspace: Path,
        stdout: str,
    ) -> dict[str, int | None]:
        if result_format == "junit":
            return parse_junit_xml(workspace / ".coderoll-results.xml")
        if result_format == "tap":
            return parse_tap_output(stdout)
        return {
            "tests_total": None,
            "tests_failed": None,
            "tests_errors": None,
            "tests_skipped": None,
            "tests_passed": None,
        }

    def _execution_result(
        self,
        task: Task,
        candidate: Candidate,
        image: str,
        sandbox_meta: dict[str, Any],
        phase: str,
        exit_code: int,
        duration_ms: int,
        timed_out: bool,
        error: str | None,
        build_exit_code: int | None,
        build_stdout: str,
        build_stderr: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            task_id=task.id,
            candidate_id=candidate.id,
            exit_code=exit_code,
            stdout=_combine_outputs(build_stdout, build_stderr, "", ""),
            stderr=build_stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
            error=error,
            sandbox=sandbox_meta,
            language=task.language,
            image=image,
            phase=phase,
            build_exit_code=build_exit_code,
            build_stdout=build_stdout,
            build_stderr=build_stderr,
            test_exit_code=None,
            test_stdout="",
            test_stderr="",
        )

    def _prepared_result(
        self,
        config_id: str,
        candidate: Candidate,
        image: str,
        sandbox_meta: dict[str, Any],
        phase: str,
        exit_code: int,
        error: str | None,
        duration_ms: int,
        timed_out: bool,
        command_results: list[CommandResult],
        setup_stdout: str,
        setup_stderr: str,
        setup_duration_ms: int,
        setup_passed: bool,
        language: str | None,
    ) -> ExecutionResult:
        tests = _aggregate_tests([result for result in command_results if result.phase == "eval"])
        eval_results = [result for result in command_results if result.phase == "eval"]
        stdout = "\n".join(
            _section(result.name or result.phase, result.stdout)
            for result in command_results
            if result.stdout
        )
        stderr = "\n".join(
            _section(result.name or result.phase, result.stderr)
            for result in command_results
            if result.stderr
        )
        test_stdout = "\n".join(
            _section(result.name or "eval", result.stdout)
            for result in eval_results
            if result.stdout
        )
        test_stderr = "\n".join(
            _section(result.name or "eval", result.stderr)
            for result in eval_results
            if result.stderr
        )
        setup_exit_code = 0 if setup_passed else next(
            (result.exit_code for result in command_results if result.phase == "setup" and result.exit_code != 0),
            None,
        )
        return ExecutionResult(
            task_id=config_id,
            candidate_id=candidate.id,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
            error=error,
            sandbox=sandbox_meta,
            language=language or "",
            image=image,
            phase=phase,
            test_exit_code=exit_code,
            test_stdout=test_stdout,
            test_stderr=test_stderr,
            setup_exit_code=setup_exit_code,
            setup_stdout=setup_stdout,
            setup_stderr=setup_stderr,
            setup_duration_ms=setup_duration_ms,
            setup_passed=setup_passed,
            command_results=command_results,
            **tests,
        )

    def _copy_support_files(
        self,
        task_root: Path,
        workspace: Path,
        skip_relpaths: set[str] | None = None,
    ) -> None:
        skip_relpaths = skip_relpaths or set()
        for source in task_root.rglob("*"):
            if source.is_dir():
                continue
            relative = source.relative_to(task_root)
            rel_posix = relative.as_posix()
            if rel_posix in skip_relpaths:
                continue
            if _should_skip(relative):
                continue

            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def _sandbox_meta(self, workspace: Path, image: str) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "type": "docker_cli",
            "image": image,
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


def _docker_error(image: str, stderr: str, exit_code: int | None) -> str | None:
    if exit_code == 125 and _looks_like_missing_image(stderr):
        return (
            f"Docker image '{image}' was not found. "
            "Run `coderoll build-image --runtime <language>` before running evaluations."
        )
    return None


def _combine_outputs(
    build_stdout: str,
    build_stderr: str,
    test_stdout: str,
    test_stderr: str,
) -> str:
    if not build_stdout and not build_stderr:
        return test_stdout
    sections = [
        ("build stdout", build_stdout),
        ("build stderr", build_stderr),
        ("test stdout", test_stdout),
        ("test stderr", test_stderr),
    ]
    return "\n".join(
        f"--- {name} ---\n{text}" for name, text in sections if text
    )


def _combine_errors(build_stderr: str, test_stderr: str) -> str:
    if build_stderr and test_stderr:
        return f"--- build stderr ---\n{build_stderr}\n--- test stderr ---\n{test_stderr}"
    return test_stderr or build_stderr


def _section(name: str, text: str) -> str:
    if not text:
        return ""
    return f"--- {name} ---\n{text}"


def _aggregate_tests(results: list[CommandResult]) -> dict[str, int | None]:
    keys = [
        "tests_total",
        "tests_passed",
        "tests_failed",
        "tests_errors",
        "tests_skipped",
    ]
    totals: dict[str, int | None] = {}
    for key in keys:
        values = [getattr(result, key) for result in results]
        known = [value for value in values if value is not None]
        totals[key] = sum(known) if known else None
    return totals
