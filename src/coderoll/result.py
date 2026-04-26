from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommandResult:
    name: str | None
    command: str
    phase: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    tests_total: int | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    tests_errors: int | None = None
    tests_skipped: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "phase": self.phase,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "tests_total": self.tests_total,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_errors": self.tests_errors,
            "tests_skipped": self.tests_skipped,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommandResult":
        return cls(
            name=_optional_str(data.get("name")),
            command=str(data.get("command", "")),
            phase=str(data.get("phase", "")),
            exit_code=int(data.get("exit_code", -1)),
            stdout=str(data.get("stdout", "")),
            stderr=str(data.get("stderr", "")),
            duration_ms=int(data.get("duration_ms", 0)),
            timed_out=bool(data.get("timed_out", False)),
            tests_total=_optional_int(data.get("tests_total")),
            tests_passed=_optional_int(data.get("tests_passed")),
            tests_failed=_optional_int(data.get("tests_failed")),
            tests_errors=_optional_int(data.get("tests_errors")),
            tests_skipped=_optional_int(data.get("tests_skipped")),
        )


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
    language: str = "python"
    image: str | None = None
    phase: str = "test"
    build_exit_code: int | None = None
    build_stdout: str = ""
    build_stderr: str = ""
    test_exit_code: int | None = None
    test_stdout: str = ""
    test_stderr: str = ""
    tests_total: int | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    tests_errors: int | None = None
    tests_skipped: int | None = None
    setup_exit_code: int | None = None
    setup_stdout: str = ""
    setup_stderr: str = ""
    setup_duration_ms: int = 0
    setup_passed: bool | None = None
    command_results: list[CommandResult] = field(default_factory=list)


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
    language: str | None = None
    image: str | None = None
    phase: str | None = None
    build_passed: bool | None = None
    build_exit_code: int | None = None
    tests_total: int | None = None
    tests_passed: int | None = None
    tests_failed: int | None = None
    tests_errors: int | None = None
    tests_skipped: int | None = None
    score_details: dict[str, Any] | None = None
    build_stdout: str = ""
    build_stderr: str = ""
    test_stdout: str = ""
    test_stderr: str = ""
    config_id: str | None = None
    candidate_mode: str | None = None
    workspace_mode: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    files_hash: str = ""
    setup_passed: bool | None = None
    setup_exit_code: int | None = None
    setup_stdout: str = ""
    setup_stderr: str = ""
    setup_duration_ms: int = 0
    command_results: list[CommandResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "task_id": self.task_id,
            "config_id": self.config_id,
            "candidate_id": self.candidate_id,
            "candidate_mode": self.candidate_mode,
            "workspace_mode": self.workspace_mode,
            "prompt": self.prompt,
            "code": self.code,
            "files": self.files,
            "code_hash": self.code_hash,
            "files_hash": self.files_hash,
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
            "language": self.language,
            "image": self.image,
            "phase": self.phase,
            "build_passed": self.build_passed,
            "build_exit_code": self.build_exit_code,
            "tests_total": self.tests_total,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_errors": self.tests_errors,
            "tests_skipped": self.tests_skipped,
            "score_details": self.score_details or {},
            "build_stdout": self.build_stdout,
            "build_stderr": self.build_stderr,
            "test_stdout": self.test_stdout,
            "test_stderr": self.test_stderr,
            "setup_passed": self.setup_passed,
            "setup_exit_code": self.setup_exit_code,
            "setup_stdout": self.setup_stdout,
            "setup_stderr": self.setup_stderr,
            "setup_duration_ms": self.setup_duration_ms,
            "command_results": [result.to_dict() for result in self.command_results],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        return cls(
            run_id=str(data.get("run_id", "")),
            created_at=str(data.get("created_at", "")),
            task_id=str(data.get("task_id", "")),
            config_id=_optional_str(data.get("config_id")),
            candidate_id=str(data.get("candidate_id", "")),
            candidate_mode=_optional_str(data.get("candidate_mode")),
            workspace_mode=_optional_str(data.get("workspace_mode")),
            prompt=str(data.get("prompt", "")),
            code=str(data.get("code", "")),
            files=data.get("files") if isinstance(data.get("files"), dict) else {},
            code_hash=str(data.get("code_hash", "")),
            files_hash=str(data.get("files_hash", "")),
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
            language=_optional_str(data.get("language")),
            image=_optional_str(data.get("image")),
            phase=_optional_str(data.get("phase")),
            build_passed=data.get("build_passed") if isinstance(data.get("build_passed"), bool) else None,
            build_exit_code=_optional_int(data.get("build_exit_code")),
            tests_total=_optional_int(data.get("tests_total")),
            tests_passed=_optional_int(data.get("tests_passed")),
            tests_failed=_optional_int(data.get("tests_failed")),
            tests_errors=_optional_int(data.get("tests_errors")),
            tests_skipped=_optional_int(data.get("tests_skipped")),
            score_details=data.get("score_details") if isinstance(data.get("score_details"), dict) else {},
            build_stdout=str(data.get("build_stdout", "")),
            build_stderr=str(data.get("build_stderr", "")),
            test_stdout=str(data.get("test_stdout", data.get("stdout", ""))),
            test_stderr=str(data.get("test_stderr", data.get("stderr", ""))),
            setup_passed=data.get("setup_passed") if isinstance(data.get("setup_passed"), bool) else None,
            setup_exit_code=_optional_int(data.get("setup_exit_code")),
            setup_stdout=str(data.get("setup_stdout", "")),
            setup_stderr=str(data.get("setup_stderr", "")),
            setup_duration_ms=int(data.get("setup_duration_ms", 0) or 0),
            command_results=_command_results_from_data(data.get("command_results")),
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


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _command_results_from_data(value: Any) -> list[CommandResult]:
    if not isinstance(value, list):
        return []
    results: list[CommandResult] = []
    for item in value:
        if isinstance(item, dict):
            results.append(CommandResult.from_dict(item))
    return results
