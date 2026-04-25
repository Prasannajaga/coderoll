from concurrent.futures import ThreadPoolExecutor, as_completed
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
            code=candidate.code,
            code_hash=sha256_text(candidate.code),
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
        )


def _derive_record_error(execution: ExecutionResult) -> str | None:
    if execution.error:
        return execution.error
    if execution.exit_code == 0:
        return None

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
