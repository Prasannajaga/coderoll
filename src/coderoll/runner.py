from concurrent.futures import ThreadPoolExecutor, as_completed
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
from .file_workspace import write_candidate_to_workspace
from .hashing import sha256_file, sha256_text
from .project import copy_project_to_workspace
from .result import ExecutionResult, RunRecord, RunResults
from .stores.jsonl import JsonlStore
from .task import Task


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
    from .evaluators.pytest_eval import PytestEvaluator
    from .sandboxes.docker_cli import DockerSandbox

    sandbox = DockerSandbox(
        image=config.sandbox.image,
        timeout=config.sandbox.timeout,
        memory=config.sandbox.memory,
        cpus=config.sandbox.cpus,
        pids_limit=config.sandbox.pids_limit,
        network=config.sandbox.network,
    )
    evaluator = PytestEvaluator()
    if config.mode == "project":
        records = [_run_project_mode(config, sandbox, evaluator)]
    elif config.mode == "file":
        records = _run_file_mode(config, sandbox, evaluator)
    else:
        raise CandidateError("mode must be one of: project, file")

    if records:
        JsonlStore(config.output_path).append_many(records)
    return RunResults(records=records)


def _run_file_mode(
    config: RunConfig,
    sandbox: Any,
    evaluator: Any,
) -> list[RunRecord]:
    if config.candidates is None:
        raise CandidateError("candidates section is required when mode=file")
    candidates = Candidate.load_many(config.candidates, config.file)
    if not candidates:
        raise CandidateError("No candidates were loaded from config candidates.path")
    if config.runner.workers == 1:
        return [_run_file_candidate(config, sandbox, evaluator, candidate) for candidate in candidates]

    ordered: list[RunRecord | None] = [None] * len(candidates)
    with ThreadPoolExecutor(max_workers=config.runner.workers) as executor:
        future_to_index = {
            executor.submit(_run_file_candidate, config, sandbox, evaluator, candidate): index
            for index, candidate in enumerate(candidates)
        }
        for future in as_completed(future_to_index):
            ordered[future_to_index[future]] = future.result()
    return [record for record in ordered if record is not None]


def _run_project_mode(
    config: RunConfig,
    sandbox: Any,
    evaluator: Any,
) -> RunRecord:
    if config.project is None:
        raise CandidateError("project section is required when mode=project")
    temp_dir = PathLikeTemp()
    candidate_id = config.project.id or config.project.path.name
    try:
        workspace = Path(temp_dir.path) / "workspace"
        copy_project_to_workspace(config.project, workspace)
        execution = sandbox.run_workspace(
            workspace_path=workspace,
            setup_commands=config.setup.commands,
            eval_commands=config.eval.commands,
            task_id=config.id,
            candidate_id=candidate_id,
            stop_on_first_failure=config.eval.stop_on_first_failure,
        )
    except Exception as exc:  # noqa: BLE001
        execution = ExecutionResult(
            task_id=config.id,
            candidate_id=candidate_id,
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

    return _record_from_execution(
        config=config,
        execution=execution,
        evaluator=evaluator,
        candidate_id=candidate_id,
        candidate_mode="project",
        files={},
        code="",
        metadata={"source": "project", "project_path": str(config.project.path)},
        project_path=str(config.project.path),
    )


def _run_file_candidate(
    config: RunConfig,
    sandbox: Any,
    evaluator: Any,
    candidate: Candidate,
) -> RunRecord:
    temp_dir = PathLikeTemp()
    try:
        workspace = Path(temp_dir.path) / "workspace"
        write_candidate_to_workspace(candidate, workspace)
        execution = sandbox.run_workspace(
            workspace_path=workspace,
            setup_commands=config.setup.commands,
            eval_commands=config.eval.commands,
            task_id=config.id,
            candidate_id=candidate.id,
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

    metadata = dict(candidate.metadata)
    metadata["source"] = candidate.source
    return _record_from_execution(
        config=config,
        execution=execution,
        evaluator=evaluator,
        candidate_id=candidate.id,
        candidate_mode="file",
        files=candidate.files,
        code=candidate.code or "",
        metadata=metadata,
        project_path=None,
    )


def _record_from_execution(
    config: RunConfig,
    execution: ExecutionResult,
    evaluator: Any,
    candidate_id: str,
    candidate_mode: str,
    files: dict[str, str],
    code: str,
    metadata: dict[str, Any],
    project_path: str | None,
) -> RunRecord:
    score = evaluator.score(execution)
    setup_results = [result for result in execution.command_results if result.phase == "setup"]
    return RunRecord(
        run_id=f"run_{uuid4().hex}",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        task_id=config.id,
        config_id=config.id,
        mode=config.mode,
        candidate_id=candidate_id,
        candidate_mode=candidate_mode,
        project_path=project_path,
        prompt="",
        code=code,
        files=files,
        code_hash=sha256_text(code),
        files_hash=_files_hash(files),
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
        setup_results=setup_results,
        command_results=execution.command_results,
    )


def _files_hash(files: dict[str, str]) -> str:
    if not files:
        return ""
    return sha256_text(json.dumps(files, sort_keys=True, ensure_ascii=False))


class PathLikeTemp:
    def __init__(self) -> None:
        self.path = tempfile.mkdtemp(prefix="coderoll_")

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)
