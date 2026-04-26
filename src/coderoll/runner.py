from concurrent.futures import ThreadPoolExecutor, as_completed
from fnmatch import fnmatch
import json
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any
from uuid import uuid4

from .candidate import Candidate
from .config import RunConfig
from .errors import CandidateError
from .hashing import sha256_file, sha256_text
from .result import ExecutionResult, RunRecord, RunResults
from .stores.jsonl import JsonlStore
from .task import Task
from .workspace import prepare_workspace, safe_copy_candidate_directory, safe_write_candidate_files


class Runner:
    def __init__(self, sandbox: Any, evaluator: Any, store: Any | None = None) -> None:
        self.sandbox = sandbox
        self.evaluator = evaluator
        self.store = store

    def run(self, task: Task, candidates: list[Candidate], workers: int = 1) -> RunResults:
        if workers < 1:
            raise ValueError("workers must be >= 1")

        test_hash = sha256_file(task.test_path)

        if workers == 1:
            records = [self._run_one(task, candidate, test_hash) for candidate in candidates]
        else:
            records = self._run_parallel(task, candidates, test_hash, workers)

        if self.store is not None and records:
            self.store.append_many(records)

        return RunResults(records=records)

    def run_strings(self, task: Task, codes: list[str], workers: int = 1) -> RunResults:
        candidates = [Candidate.from_string(code) for code in codes]
        return self.run(task, candidates, workers=workers)

    def _run_parallel(
        self, task: Task, candidates: list[Candidate], test_hash: str, workers: int
    ) -> list[RunRecord]:
        ordered: list[RunRecord | None] = [None] * len(candidates)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(self._run_one, task, candidate, test_hash): index
                for index, candidate in enumerate(candidates)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                ordered[index] = future.result()

        return [record for record in ordered if record is not None]

    def _run_one(self, task: Task, candidate: Candidate, test_hash: str) -> RunRecord:
        try:
            execution = self.sandbox.run(task, candidate)
        except Exception as exc:  # noqa: BLE001
            execution = ExecutionResult(
                task_id=task.id,
                candidate_id=candidate.id,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=0,
                timed_out=False,
                error=str(exc),
                sandbox={"type": type(self.sandbox).__name__},
                language=task.language,
                image=task.image,
                phase="infra",
                test_exit_code=-1,
            )

        score = self.evaluator.score(execution)
        record_error = _derive_record_error(execution)

        metadata = dict(candidate.metadata)
        if "source" not in metadata:
            metadata["source"] = candidate.source

        return RunRecord(
            run_id=f"run_{uuid4().hex}",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            task_id=task.id,
            candidate_id=candidate.id,
            prompt=task.prompt,
            code=candidate.code or "",
            code_hash=sha256_text(candidate.code or ""),
            test_hash=test_hash,
            passed=score.passed,
            score=score.value,
            exit_code=execution.exit_code,
            stdout=execution.stdout,
            stderr=execution.stderr,
            duration_ms=execution.duration_ms,
            timed_out=execution.timed_out,
            error=record_error,
            sandbox=execution.sandbox,
            metadata=metadata,
            language=execution.language,
            image=execution.image,
            phase=execution.phase,
            build_passed=(
                execution.build_exit_code is None or execution.build_exit_code == 0
            ),
            build_exit_code=execution.build_exit_code,
            tests_total=execution.tests_total,
            tests_passed=execution.tests_passed,
            tests_failed=execution.tests_failed,
            tests_errors=execution.tests_errors,
            tests_skipped=execution.tests_skipped,
            score_details=score.details,
            build_stdout=execution.build_stdout,
            build_stderr=execution.build_stderr,
            test_stdout=execution.test_stdout,
            test_stderr=execution.test_stderr,
            candidate_mode=candidate.mode,
            files=candidate.files,
            files_hash=_files_hash(candidate.files),
            setup_passed=execution.setup_passed,
            setup_exit_code=execution.setup_exit_code,
            setup_stdout=execution.setup_stdout,
            setup_stderr=execution.setup_stderr,
            setup_duration_ms=execution.setup_duration_ms,
            command_results=execution.command_results,
        )


def _derive_record_error(execution: ExecutionResult) -> str | None:
    if execution.error:
        return execution.error
    if execution.exit_code == 0:
        return None
    for result in execution.command_results:
        if result.phase == "eval" and result.exit_code != 0:
            stderr_summary = _first_non_empty_line(result.stderr)
            if stderr_summary:
                return stderr_summary
            stdout_summary = _stdout_failure_summary(result.stdout)
            if stdout_summary:
                return stdout_summary
            return f"Command exited with code {result.exit_code}: {result.command}"
    for result in execution.command_results:
        if result.phase == "setup" and result.exit_code != 0:
            stderr_summary = _first_non_empty_line(result.stderr)
            if stderr_summary:
                return stderr_summary
            stdout_summary = _first_non_empty_line(result.stdout)
            if stdout_summary:
                return stdout_summary
            return f"Setup command exited with code {result.exit_code}: {result.command}"

    stderr_summary = _first_non_empty_line(execution.stderr)
    if stderr_summary:
        return stderr_summary

    stdout_summary = _stdout_failure_summary(execution.stdout)
    if stdout_summary:
        return stdout_summary

    return f"Process exited with code {execution.exit_code}"


def _stdout_failure_summary(stdout: str) -> str | None:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("FAILED "):
            return line
    for line in lines:
        if line.startswith("E   "):
            return line[4:].strip()
    return _first_non_empty_line(stdout)


def _first_non_empty_line(text: str) -> str | None:
    for raw in text.splitlines():
        line = raw.strip()
        if line:
            return line
    return None


def run_from_config(config: RunConfig) -> RunResults:
    from .candidate import Candidate
    from .evaluators.pytest_eval import PytestEvaluator
    from .sandboxes.docker_cli import DockerSandbox

    if "workspace" not in config.raw and "eval" not in config.raw:
        if config.task_path is None:
            raise CandidateError("Legacy config requires task.path")
        task = Task.from_dir(config.task_path)
        candidates = Candidate.from_jsonl(config.candidates_path)
        if not candidates:
            raise CandidateError("No candidates were loaded from config candidates.path")
        sandbox = DockerSandbox(
            image=config.sandbox.image,
            timeout=config.sandbox.timeout,
            memory=config.sandbox.memory,
            cpus=config.sandbox.cpus,
            pids_limit=config.sandbox.pids_limit,
            network=config.sandbox.network,
        )
        runner = Runner(
            sandbox=sandbox,
            evaluator=PytestEvaluator(),
            store=JsonlStore(config.output_path),
        )
        return runner.run(task, candidates, workers=config.runner.workers)

    candidates = Candidate.load_many(
        config.candidates.path,
        type=config.candidates.type,
        mode=config.candidates.mode,
        entry_file=config.candidates.entry_file,
    )
    if not candidates:
        raise CandidateError("No candidates were loaded from config candidates.path")
    sandbox = DockerSandbox(
        image=config.sandbox.image,
        timeout=config.sandbox.timeout,
        memory=config.sandbox.memory,
        cpus=config.sandbox.cpus,
        pids_limit=config.sandbox.pids_limit,
        network=config.sandbox.network,
    )
    records = _run_config_candidates(config, sandbox, PytestEvaluator(), candidates)
    if records:
        JsonlStore(config.output_path).append_many(records)
    return RunResults(records=records)


def _run_config_candidates(
    config: RunConfig,
    sandbox: Any,
    evaluator: Any,
    candidates: list[Candidate],
) -> list[RunRecord]:
    if config.runner.workers == 1:
        return [_run_config_one(config, sandbox, evaluator, candidate) for candidate in candidates]

    ordered: list[RunRecord | None] = [None] * len(candidates)
    with ThreadPoolExecutor(max_workers=config.runner.workers) as executor:
        future_to_index = {
            executor.submit(_run_config_one, config, sandbox, evaluator, candidate): index
            for index, candidate in enumerate(candidates)
        }
        for future in as_completed(future_to_index):
            ordered[future_to_index[future]] = future.result()
    return [record for record in ordered if record is not None]


def _run_config_one(
    config: RunConfig,
    sandbox: Any,
    evaluator: Any,
    candidate: Candidate,
) -> RunRecord:
    temp_dir = PathLikeTemp()
    warnings: list[str] = []
    try:
        workspace = prepare_workspace(config.workspace, temp_dir.path)
        if candidate.directory is not None:
            safe_copy_candidate_directory(
                candidate.directory,
                workspace,
                include=["**/*"],
                exclude=config.workspace.exclude,
            )
        else:
            entry_file = config.candidates.entry_file or str(candidate.metadata.get("entry_file", ""))
            safe_write_candidate_files(workspace, candidate, entry_file=entry_file or None)

        dependency_commands = _candidate_dependency_commands(
            candidate,
            allow=config.setup.allow_candidate_dependencies,
            warnings=warnings,
        )
        image = config.sandbox.image
        if not image:
            raise CandidateError("sandbox.image is required for config workspace evaluations")
        execution = sandbox.run_prepared_workspace(
            config_id=config.id,
            candidate=candidate,
            workspace=workspace,
            image=image,
            setup_commands=config.setup.commands,
            dependency_commands=dependency_commands,
            eval_commands=config.eval.commands,
            default_result_format=config.eval.result_format,
            setup_timeout=config.setup.dependency_install_timeout or config.sandbox.timeout,
            stop_on_first_failure=config.eval.stop_on_first_failure,
        )
    except Exception as exc:  # noqa: BLE001
        execution = ExecutionResult(
            task_id=config.id,
            candidate_id=candidate.id,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_ms=0,
            timed_out=False,
            error=str(exc),
            sandbox={"type": type(sandbox).__name__},
            phase="infra",
            setup_passed=False,
        )
    finally:
        if not sandbox.keep_workspace:
            temp_dir.cleanup()

    score = evaluator.score(execution)
    metadata = dict(candidate.metadata)
    metadata["source"] = candidate.source
    if warnings:
        metadata["warnings"] = warnings
    if candidate.directory is not None:
        metadata["directory"] = str(candidate.directory)

    record_files = candidate.files
    if candidate.directory is not None:
        record_files = _read_directory_candidate_files(
            candidate.directory,
            exclude=config.workspace.exclude,
        )

    return RunRecord(
        run_id=f"run_{uuid4().hex}",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        task_id=config.id,
        config_id=config.id,
        candidate_id=candidate.id,
        candidate_mode=config.candidates.mode,
        workspace_mode=config.workspace.mode,
        prompt="",
        code=candidate.code or "",
        files=record_files,
        code_hash=sha256_text(candidate.code or ""),
        files_hash=_files_hash(record_files),
        test_hash="",
        passed=score.passed,
        score=score.value,
        exit_code=execution.exit_code,
        stdout=execution.stdout,
        stderr=execution.stderr,
        duration_ms=execution.duration_ms,
        timed_out=execution.timed_out,
        error=_derive_record_error(execution),
        sandbox=execution.sandbox,
        metadata=metadata,
        language=execution.language,
        image=execution.image,
        phase=execution.phase,
        build_passed=None,
        build_exit_code=execution.build_exit_code,
        tests_total=execution.tests_total,
        tests_passed=execution.tests_passed,
        tests_failed=execution.tests_failed,
        tests_errors=execution.tests_errors,
        tests_skipped=execution.tests_skipped,
        score_details=score.details,
        build_stdout=execution.build_stdout,
        build_stderr=execution.build_stderr,
        test_stdout=execution.test_stdout,
        test_stderr=execution.test_stderr,
        setup_passed=execution.setup_passed,
        setup_exit_code=execution.setup_exit_code,
        setup_stdout=execution.setup_stdout,
        setup_stderr=execution.setup_stderr,
        setup_duration_ms=execution.setup_duration_ms,
        command_results=execution.command_results,
    )


def _candidate_dependency_commands(
    candidate: Candidate,
    allow: bool,
    warnings: list[str],
) -> list[str]:
    if not candidate.dependencies:
        return []
    if not allow:
        warnings.append("candidate dependencies ignored because setup.allow_candidate_dependencies is false")
        return []
    commands: list[str] = []
    pip_packages = candidate.dependencies.get("pip")
    if pip_packages:
        if not isinstance(pip_packages, list):
            raise CandidateError("dependencies.pip must be a list")
        commands.append("python -m pip install " + " ".join(str(package) for package in pip_packages))
    npm_packages = candidate.dependencies.get("npm")
    if npm_packages:
        if not isinstance(npm_packages, list):
            raise CandidateError("dependencies.npm must be a list")
        commands.append("npm install " + " ".join(str(package) for package in npm_packages))
    raw_commands = candidate.dependencies.get("commands")
    if raw_commands:
        if not isinstance(raw_commands, list):
            raise CandidateError("dependencies.commands must be a list")
        commands.extend(str(command) for command in raw_commands)
    return commands


def _files_hash(files: dict[str, str]) -> str:
    if not files:
        return ""
    return sha256_text(json.dumps(files, sort_keys=True, ensure_ascii=False))


def _read_directory_candidate_files(candidate_dir: Path, exclude: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    excluded_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        ".coderoll",
    }
    for source in sorted(candidate_dir.rglob("*")):
        if source.is_symlink() or source.is_dir():
            continue
        relative = source.relative_to(candidate_dir)
        rel = relative.as_posix()
        if any(part in excluded_dirs for part in relative.parts):
            continue
        if any(fnmatch(rel, pattern) for pattern in exclude):
            continue
        try:
            files[rel] = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            files[rel] = source.read_bytes().hex()
    return files


class PathLikeTemp:
    def __init__(self) -> None:
        self.path = tempfile.mkdtemp(prefix="coderoll_")

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)
