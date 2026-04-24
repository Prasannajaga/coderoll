from coderoll.rankers.simple import rank_records
from coderoll.result import RunRecord, RunResults


def _record(candidate_id: str, score: float, passed: bool, duration_ms: int) -> RunRecord:
    return RunRecord(
        run_id=f"run_{candidate_id}",
        created_at="2026-01-01T00:00:00Z",
        task_id="task",
        candidate_id=candidate_id,
        prompt="prompt",
        code="code",
        code_hash="hash",
        test_hash="testhash",
        passed=passed,
        score=score,
        exit_code=0 if passed else 1,
        stdout="",
        stderr="",
        duration_ms=duration_ms,
        timed_out=False,
        error=None,
        sandbox={"type": "docker_cli"},
        metadata={},
    )


def test_rank_records_order() -> None:
    records = [
        _record("b", score=1.0, passed=True, duration_ms=30),
        _record("a", score=1.0, passed=True, duration_ms=10),
        _record("c", score=0.0, passed=False, duration_ms=5),
    ]

    ranked = rank_records(records)

    assert [record.candidate_id for record in ranked] == ["a", "b", "c"]


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
