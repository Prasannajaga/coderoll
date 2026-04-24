from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Any
from uuid import uuid4

from .candidate import Candidate
from .hashing import sha256_file, sha256_text
from .result import ExecutionResult, RunRecord, RunResults
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
            )

        score = self.evaluator.score(execution)

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
            error=execution.error,
            sandbox=execution.sandbox,
            metadata=metadata,
        )
