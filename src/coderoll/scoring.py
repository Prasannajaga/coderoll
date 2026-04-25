from dataclasses import dataclass
from typing import Any

from .result import ExecutionResult


@dataclass
class ScoreBreakdown:
    value: float
    passed: bool
    test_score: float
    build_score: float
    runtime_score: float
    timeout_penalty: float
    details: dict[str, Any]


def compute_score(execution: ExecutionResult) -> ScoreBreakdown:
    timeout_penalty = 0.25 if execution.timed_out else 0.0
    final_test_exit_code = (
        execution.test_exit_code
        if execution.test_exit_code is not None
        else execution.exit_code
    )

    if execution.phase == "infra":
        build_score = 0.0
    elif execution.build_exit_code is None:
        build_score = 1.0
    elif execution.build_exit_code == 0:
        build_score = 1.0
    else:
        build_score = 0.0

    if execution.tests_total is not None and execution.tests_total > 0:
        test_score = (execution.tests_passed or 0) / execution.tests_total
    else:
        test_score = 1.0 if final_test_exit_code == 0 else 0.0

    runtime_score = 0.0 if execution.timed_out or execution.phase == "infra" else 1.0
    if build_score == 0.0:
        value = 0.0
    else:
        value = (test_score * 0.85) + (build_score * 0.10) + (runtime_score * 0.05) - timeout_penalty
    value = min(max(value, 0.0), 1.0)

    build_passed = execution.build_exit_code is None or execution.build_exit_code == 0
    passed = build_passed and final_test_exit_code == 0 and not execution.timed_out

    details = {
        "test_score": test_score,
        "build_score": build_score,
        "runtime_score": runtime_score,
        "timeout_penalty": timeout_penalty,
        "phase": execution.phase,
        "tests_total": execution.tests_total,
        "tests_passed": execution.tests_passed,
        "tests_failed": execution.tests_failed,
        "tests_errors": execution.tests_errors,
        "tests_skipped": execution.tests_skipped,
    }
    return ScoreBreakdown(
        value=value,
        passed=passed,
        test_score=test_score,
        build_score=build_score,
        runtime_score=runtime_score,
        timeout_penalty=timeout_penalty,
        details=details,
    )
