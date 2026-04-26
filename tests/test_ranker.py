from types import SimpleNamespace

import pytest

from coderoll.rankers.simple import (
    candidate_size,
    debug_rank_key,
    default_rank_key,
    explain_rank,
    rank_records,
    strict_rank_key,
    test_pass_ratio,
)
from coderoll.result import RunRecord, RunResults


def _record(
    candidate_id: str,
    score: float = 0.0,
    passed: bool = False,
    duration_ms: int = 0,
    **overrides: object,
) -> RunRecord:
    payload = {
        "run_id": f"run_{candidate_id}",
        "created_at": "2026-01-01T00:00:00Z",
        "task_id": "task",
        "candidate_id": candidate_id,
        "prompt": "prompt",
        "code": "code",
        "code_hash": "hash",
        "test_hash": "testhash",
        "passed": passed,
        "score": score,
        "exit_code": 0 if passed else 1,
        "stdout": "",
        "stderr": "",
        "duration_ms": duration_ms,
        "timed_out": False,
        "error": None,
        "sandbox": {"type": "docker_cli"},
        "metadata": {},
        "phase": "complete" if passed else "eval",
        "setup_passed": True,
        "tests_total": None,
        "tests_passed": None,
        "tests_failed": None,
        "tests_errors": None,
        "tests_skipped": None,
    }
    payload.update(overrides)
    return RunRecord(**payload)


def test_default_passed_beats_failed_even_with_higher_failed_score() -> None:
    records = [
        _record("passed", score=0.90, passed=True, duration_ms=50),
        _record("failed", score=0.95, passed=False, duration_ms=10),
    ]

    ranked = rank_records(records, profile="default")

    assert [record.candidate_id for record in ranked] == ["passed", "failed"]


def test_default_higher_score_wins_among_passed_records() -> None:
    records = [
        _record("low", score=0.70, passed=True, duration_ms=10),
        _record("high", score=0.90, passed=True, duration_ms=100),
    ]

    ranked = rank_records(records, profile="default")

    assert [record.candidate_id for record in ranked] == ["high", "low"]


def test_default_lower_duration_breaks_tie() -> None:
    records = [
        _record("slow", score=1.0, passed=True, duration_ms=30),
        _record("fast", score=1.0, passed=True, duration_ms=10),
    ]

    ranked = rank_records(records, profile="default")

    assert [record.candidate_id for record in ranked] == ["fast", "slow"]


def test_strict_timeout_is_penalized() -> None:
    records = [
        _record("ok", score=0.8, passed=True, duration_ms=20, timed_out=False),
        _record("timeout", score=0.8, passed=True, duration_ms=20, timed_out=True, phase="timeout"),
    ]

    ranked = rank_records(records, profile="strict")

    assert [record.candidate_id for record in ranked] == ["ok", "timeout"]


def test_strict_setup_failure_is_penalized() -> None:
    records = [
        _record("setup_ok", score=0.8, passed=True, setup_passed=True),
        _record("setup_fail", score=0.8, passed=True, setup_passed=False, phase="setup"),
    ]

    ranked = rank_records(records, profile="strict")

    assert [record.candidate_id for record in ranked] == ["setup_ok", "setup_fail"]


def test_strict_failed_error_skipped_tests_are_penalized() -> None:
    records = [
        _record("clean", score=0.8, passed=True, tests_failed=0, tests_errors=0, tests_skipped=0),
        _record("has_skips", score=0.8, passed=True, tests_failed=0, tests_errors=0, tests_skipped=1),
        _record("has_errors", score=0.8, passed=True, tests_failed=0, tests_errors=1, tests_skipped=0),
        _record("has_failures", score=0.8, passed=True, tests_failed=1, tests_errors=0, tests_skipped=0),
    ]

    ranked = rank_records(records, profile="strict")

    assert [record.candidate_id for record in ranked] == [
        "clean",
        "has_skips",
        "has_errors",
        "has_failures",
    ]


def test_strict_higher_score_breaks_remaining_ties() -> None:
    records = [
        _record("low", score=0.50, passed=True, timed_out=False, setup_passed=True),
        _record("high", score=0.90, passed=True, timed_out=False, setup_passed=True),
    ]

    ranked = rank_records(records, profile="strict")

    assert [record.candidate_id for record in ranked] == ["high", "low"]


def test_debug_phase_priority_order() -> None:
    records = [
        _record("eval", score=0.2, passed=False, phase="eval"),
        _record("setup", score=0.2, passed=False, phase="setup", setup_passed=False),
        _record("timeout", score=0.2, passed=False, phase="timeout", timed_out=True),
        _record("infra", score=0.2, passed=False, phase="infra"),
    ]

    ranked = rank_records(records, profile="debug")

    assert [record.candidate_id for record in ranked] == ["infra", "timeout", "setup", "eval"]


def test_debug_lowest_score_ranks_first_within_same_phase() -> None:
    records = [
        _record("high", score=0.9, passed=False, phase="eval"),
        _record("low", score=0.2, passed=False, phase="eval"),
    ]

    ranked = rank_records(records, profile="debug")

    assert [record.candidate_id for record in ranked] == ["low", "high"]


def test_debug_longer_duration_ranks_first_within_same_phase_and_score() -> None:
    records = [
        _record("short", score=0.2, passed=False, phase="eval", duration_ms=10),
        _record("long", score=0.2, passed=False, phase="eval", duration_ms=100),
    ]

    ranked = rank_records(records, profile="debug")

    assert [record.candidate_id for record in ranked] == ["long", "short"]


def test_test_pass_ratio_with_structured_tests() -> None:
    record = _record("r", passed=False, tests_total=4, tests_passed=3)

    assert test_pass_ratio(record) == 0.75


def test_test_pass_ratio_without_structured_tests() -> None:
    record = _record("r", passed=True, tests_total=None, tests_passed=None)

    assert test_pass_ratio(record) == 1.0


def test_candidate_size_with_files() -> None:
    record = _record("r", files={"a.py": "abc", "b.py": "de"}, code="ignored")

    assert candidate_size(record) == 5


def test_candidate_size_with_code() -> None:
    legacy = SimpleNamespace(code="abcd")

    assert candidate_size(legacy) == 4


def test_missing_fields_do_not_crash() -> None:
    legacy = SimpleNamespace(candidate_id="legacy")

    assert isinstance(default_rank_key(legacy), tuple)
    assert isinstance(strict_rank_key(legacy), tuple)
    assert isinstance(debug_rank_key(legacy), tuple)
    assert isinstance(explain_rank(legacy), dict)


def test_explain_rank_reason_for_passed_record() -> None:
    info = explain_rank(_record("ok", passed=True, phase="complete", timed_out=False, setup_passed=True))

    assert info["reason"] == "fully passed, no timeout"


def test_explain_rank_reason_for_partial_pass() -> None:
    info = explain_rank(
        _record("partial", passed=False, phase="eval", tests_total=3, tests_passed=2),
    )

    assert info["reason"] == "partial pass: 2/3 tests passed"


def test_explain_rank_reason_for_setup_failure() -> None:
    info = explain_rank(_record("setup", passed=False, phase="setup", setup_passed=False))

    assert info["reason"] == "setup failed"


def test_explain_rank_reason_for_timeout() -> None:
    info = explain_rank(_record("timeout", passed=False, phase="timeout", timed_out=True))

    assert info["reason"] == "timed out"


def test_explain_rank_reason_for_infra_failure() -> None:
    info = explain_rank(_record("infra", passed=False, phase="infra"))

    assert info["reason"] == "infra failure"


def test_unknown_profile_raises_clear_error() -> None:
    with pytest.raises(
        ValueError,
        match="Unknown ranking profile 'fast'. Allowed profiles: default, strict, debug",
    ):
        rank_records([_record("a", passed=True)], profile="fast")


def test_run_results_best_and_top_k() -> None:
    results = RunResults(
        records=[
            _record("slow_good", score=1.0, passed=True, duration_ms=20),
            _record("fast_good", score=1.0, passed=True, duration_ms=5),
            _record("bad", score=0.0, passed=False, duration_ms=1),
        ]
    )

    best = results.best()
    top_two = results.top_k(2)

    assert best is not None
    assert best.candidate_id == "fast_good"
    assert [record.candidate_id for record in top_two] == ["fast_good", "slow_good"]
