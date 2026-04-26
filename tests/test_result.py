from coderoll.result import CommandResult, RunRecord


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


def test_run_record_command_results_serialization() -> None:
    record = RunRecord.from_dict(
        {
            "run_id": "run_1",
            "created_at": "2026-01-01T00:00:00Z",
            "task_id": "task",
            "config_id": "cfg",
            "candidate_id": "cand",
            "candidate_mode": "files",
            "workspace_mode": "project",
            "prompt": "prompt",
            "code": "",
            "files": {"solution.py": "x = 1"},
            "code_hash": "hash",
            "files_hash": "fileshash",
            "test_hash": "testhash",
            "passed": True,
            "score": 1.0,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "duration_ms": 1,
            "timed_out": False,
            "error": None,
            "sandbox": {},
            "metadata": {},
            "command_results": [
                CommandResult("tests", "python -m pytest", "eval", 0, "ok", "", 1, False).to_dict()
            ],
        }
    )

    payload = record.to_dict()

    assert record.files == {"solution.py": "x = 1"}
    assert payload["command_results"][0]["command"] == "python -m pytest"
