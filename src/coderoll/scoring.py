from dataclasses import dataclass
from typing import Any

from .result import ExecutionResult


@dataclass
class ScoreBreakdown:
    value: float
    passed: bool
    test_score: float = 0.0
    build_score: float = 0.0
    runtime_score: float = 0.0
    timeout_penalty: float = 0.0
    details: dict[str, Any] | None = None


def compute_score(execution: ExecutionResult) -> ScoreBreakdown:
    if execution.command_results:
        return _compute_command_score(execution)

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


def _compute_command_score(execution: ExecutionResult) -> ScoreBreakdown:
    setup_passed = execution.setup_passed
    if setup_passed is False:
        return ScoreBreakdown(
            value=0.0,
            passed=False,
            test_score=0.0,
            build_score=0.0,
            runtime_score=1.0,
            timeout_penalty=0.0,
            details={
                "setup_score": 0.0,
                "command_scores": [],
                "timeout_penalty": 0.0,
                "phase": execution.phase,
            },
        )

    eval_results = [result for result in execution.command_results if result.phase == "eval"]
    command_scores: list[dict[str, Any]] = []
    values: list[float] = []
    for result in eval_results:
        if result.tests_total is not None and result.tests_total > 0:
            value = (result.tests_passed or 0) / result.tests_total
        else:
            value = 1.0 if result.exit_code == 0 else 0.0
        values.append(value)
        command_scores.append(
            {
                "name": result.name,
                "command": result.command,
                "score": value,
                "exit_code": result.exit_code,
                "tests_total": result.tests_total,
                "tests_passed": result.tests_passed,
                "timed_out": result.timed_out,
            }
        )

    base_score = sum(values) / len(values) if values else 0.0
    any_timeout = execution.timed_out or any(result.timed_out for result in execution.command_results)
    timeout_penalty = 0.25 if any_timeout else 0.0
    value = min(max(base_score - timeout_penalty, 0.0), 1.0)
    passed = (
        setup_passed is not False
        and bool(eval_results)
        and all(result.exit_code == 0 for result in eval_results)
        and not any_timeout
    )
    details = {
        "setup_score": 1.0 if setup_passed is not False else 0.0,
        "command_scores": command_scores,
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
        test_score=base_score,
        build_score=details["setup_score"],
        runtime_score=0.0 if any_timeout or execution.phase == "infra" else 1.0,
        timeout_penalty=timeout_penalty,
        details=details,
    )
