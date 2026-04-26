import pytest

from coderoll.result import ExecutionResult
from coderoll.result import CommandResult
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


def test_compute_score_two_commands_one_fails() -> None:
    score = compute_score(
        _execution(
            exit_code=1,
            setup_passed=True,
            command_results=[
                CommandResult(None, "typecheck", "eval", 0, "", "", 1, False),
                CommandResult(None, "test", "eval", 1, "", "", 1, False),
            ],
        )
    )

    assert score.value == pytest.approx(0.5)
    assert score.passed is False


def test_compute_score_command_structured_tests() -> None:
    score = compute_score(
        _execution(
            exit_code=1,
            setup_passed=True,
            command_results=[
                CommandResult(
                    None,
                    "test",
                    "eval",
                    1,
                    "",
                    "",
                    1,
                    False,
                    tests_total=5,
                    tests_passed=3,
                )
            ],
        )
    )

    assert score.value == pytest.approx(0.6)


def test_compute_score_setup_failure() -> None:
    score = compute_score(
        _execution(
            exit_code=1,
            setup_passed=False,
            command_results=[CommandResult(None, "setup", "setup", 1, "", "", 1, False)],
        )
    )

    assert score.value == 0.0
    assert score.passed is False


def test_compute_score_command_timeout_penalty() -> None:
    score = compute_score(
        _execution(
            exit_code=-1,
            timed_out=True,
            setup_passed=True,
            command_results=[CommandResult(None, "test", "eval", -1, "", "", 1, True)],
        )
    )

    assert score.value == 0.0
    assert score.timeout_penalty == 0.25
