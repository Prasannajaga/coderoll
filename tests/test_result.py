from coderoll.result import RunRecord


def test_run_record_from_dict_backward_compatible() -> None:
    record = RunRecord.from_dict(
        {
            "run_id": "run_1",
            "created_at": "2026-01-01T00:00:00Z",
            "task_id": "task",
            "candidate_id": "cand",
            "prompt": "prompt",
            "code": "code",
            "code_hash": "hash",
            "test_hash": "testhash",
            "passed": True,
            "score": 1.0,
            "exit_code": 0,
            "stdout": "old stdout",
            "stderr": "old stderr",
            "duration_ms": 1,
            "timed_out": False,
            "error": None,
            "sandbox": {},
            "metadata": {},
        }
    )

    assert record.language is None
    assert record.phase is None
    assert record.score_details == {}
    assert record.test_stdout == "old stdout"
    assert record.test_stderr == "old stderr"
