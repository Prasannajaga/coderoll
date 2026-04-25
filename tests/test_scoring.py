import pytest

from coderoll.result import ExecutionResult
from coderoll.scoring import compute_score


def _execution(**overrides) -> ExecutionResult:  # type: ignore[no-untyped-def]
    data = {
        "task_id": "task",
        "candidate_id": "cand",
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "duration_ms": 1,
        "timed_out": False,
        "error": None,
        "sandbox": {},
        "test_exit_code": 0,
    }
    data.update(overrides)
    return ExecutionResult(**data)


def test_compute_score_full_pass() -> None:
    score = compute_score(_execution(tests_total=3, tests_passed=3))

    assert score.value == 1.0
    assert score.passed is True


def test_compute_score_partial_pass() -> None:
    score = compute_score(_execution(test_exit_code=1, exit_code=1, tests_total=4, tests_passed=2))

    assert score.value == pytest.approx(0.575)
    assert score.passed is False


def test_compute_score_build_failure() -> None:
    score = compute_score(_execution(exit_code=1, test_exit_code=None, build_exit_code=1))

    assert score.value == 0.0
    assert score.passed is False


def test_compute_score_timeout() -> None:
    score = compute_score(_execution(exit_code=-1, test_exit_code=None, timed_out=True))

    assert score.value == 0.0
    assert score.timeout_penalty == 0.25
    assert score.passed is False
