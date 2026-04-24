from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionResult:
    task_id: str
    candidate_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    error: str | None
    sandbox: dict[str, Any]


@dataclass
class Score:
    value: float
    passed: bool
    details: dict[str, Any]


@dataclass
class RunRecord:
    run_id: str
    created_at: str
    task_id: str
    candidate_id: str
    prompt: str
    code: str
    code_hash: str
    test_hash: str
    passed: bool
    score: float
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    error: str | None
    sandbox: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "task_id": self.task_id,
            "candidate_id": self.candidate_id,
            "prompt": self.prompt,
            "code": self.code,
            "code_hash": self.code_hash,
            "test_hash": self.test_hash,
            "passed": self.passed,
            "score": self.score,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "error": self.error,
            "sandbox": self.sandbox,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        return cls(
            run_id=str(data.get("run_id", "")),
            created_at=str(data.get("created_at", "")),
            task_id=str(data.get("task_id", "")),
            candidate_id=str(data.get("candidate_id", "")),
            prompt=str(data.get("prompt", "")),
            code=str(data.get("code", "")),
            code_hash=str(data.get("code_hash", "")),
            test_hash=str(data.get("test_hash", "")),
            passed=bool(data.get("passed", False)),
            score=float(data.get("score", 0.0)),
            exit_code=int(data.get("exit_code", -1)),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            duration_ms=int(data.get("duration_ms", 0)),
            timed_out=bool(data.get("timed_out", False)),
            error=data.get("error"),
            sandbox=data.get("sandbox") if isinstance(data.get("sandbox"), dict) else {},
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )


@dataclass
class RunResults:
    records: list[RunRecord]

    def best(self) -> RunRecord | None:
        ranked = self.top_k(1)
        return ranked[0] if ranked else None

    def top_k(self, k: int) -> list[RunRecord]:
        from .rankers.simple import rank_records

        if k <= 0:
            return []
        return rank_records(self.records)[:k]

    def passed(self) -> list[RunRecord]:
        return [record for record in self.records if record.passed]

    def failed(self) -> list[RunRecord]:
        return [record for record in self.records if not record.passed]

    def summary(self) -> dict[str, Any]:
        best = self.best()
        return {
            "total": len(self.records),
            "passed": len(self.passed()),
            "failed": len(self.failed()),
            "best_score": best.score if best is not None else None,
        }
