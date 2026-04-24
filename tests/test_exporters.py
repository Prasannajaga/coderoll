from pathlib import Path
import json

from coderoll.exporters import export_preferences, export_rewards, export_sft
from coderoll.result import RunRecord


def _record(
    task_id: str,
    candidate_id: str,
    passed: bool,
    score: float,
    duration_ms: int,
    code: str | None = None,
) -> RunRecord:
    return RunRecord(
        run_id=f"run_{task_id}_{candidate_id}",
        created_at="2026-01-01T00:00:00Z",
        task_id=task_id,
        candidate_id=candidate_id,
        prompt=f"prompt {task_id}",
        code=code or f"def solution(x): return '{candidate_id}'",
        code_hash=f"hash_{candidate_id}",
        test_hash=f"testhash_{task_id}",
        passed=passed,
        score=score,
        exit_code=0 if passed else 1,
        stdout="",
        stderr="",
        duration_ms=duration_ms,
        timed_out=False,
        error=None if passed else "failed",
        sandbox={"type": "docker_cli"},
        metadata={"source": "test"},
    )


def _read_jsonl(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_export_sft_chooses_best_passing_candidate(tmp_path: Path) -> None:
    out = tmp_path / "sft.jsonl"
    records = [
        _record("t1", "slow_good", passed=True, score=1.0, duration_ms=20),
        _record("t1", "fast_good", passed=True, score=1.0, duration_ms=10),
        _record("t1", "bad", passed=False, score=0.0, duration_ms=5),
    ]

    rows = export_sft(records, out)

    assert rows == 1
    payload = _read_jsonl(out)
    assert payload[0]["candidate_id"] == "fast_good"


def test_export_sft_skips_task_with_no_passing_candidate(tmp_path: Path) -> None:
    out = tmp_path / "sft.jsonl"
    records = [
        _record("t1", "bad1", passed=False, score=0.0, duration_ms=10),
        _record("t1", "bad2", passed=False, score=0.0, duration_ms=20),
        _record("t2", "good", passed=True, score=1.0, duration_ms=10),
    ]

    rows = export_sft(records, out)

    assert rows == 1
    payload = _read_jsonl(out)
    assert payload[0]["task_id"] == "t2"


def test_export_preferences_creates_chosen_rejected_pair(tmp_path: Path) -> None:
    out = tmp_path / "pref.jsonl"
    records = [
        _record("t1", "good_fast", passed=True, score=1.0, duration_ms=10),
        _record("t1", "good_slow", passed=True, score=1.0, duration_ms=40),
        _record("t1", "fail_worse", passed=False, score=0.0, duration_ms=50),
        _record("t1", "fail_less_worse", passed=False, score=0.0, duration_ms=20),
    ]

    rows = export_preferences(records, out)

    assert rows == 1
    payload = _read_jsonl(out)
    assert payload[0]["chosen_id"] == "good_fast"
    assert payload[0]["rejected_id"] == "fail_worse"


def test_export_preferences_skips_incomplete_task(tmp_path: Path) -> None:
    out = tmp_path / "pref.jsonl"
    records = [
        _record("t1", "good_only", passed=True, score=1.0, duration_ms=10),
        _record("t2", "bad_only", passed=False, score=0.0, duration_ms=10),
    ]

    rows = export_preferences(records, out)

    assert rows == 0
    assert out.read_text(encoding="utf-8") == ""


def test_export_rewards_exports_all_records(tmp_path: Path) -> None:
    out = tmp_path / "rewards.jsonl"
    records = [
        _record("t1", "b", passed=False, score=0.0, duration_ms=10),
        _record("t1", "a", passed=True, score=1.0, duration_ms=5),
        _record("t2", "z", passed=True, score=1.0, duration_ms=7),
    ]

    rows = export_rewards(records, out)

    assert rows == 3
    payload = _read_jsonl(out)
    assert len(payload) == 3


def test_include_metadata_adds_metadata(tmp_path: Path) -> None:
    out = tmp_path / "rewards.jsonl"
    records = [_record("t1", "a", passed=True, score=1.0, duration_ms=5)]

    rows = export_rewards(records, out, include_metadata=True)

    assert rows == 1
    payload = _read_jsonl(out)
    assert "metadata" in payload[0]
    assert payload[0]["metadata"]["duration_ms"] == 5
    assert payload[0]["metadata"]["code_hash"] == "hash_a"


def test_empty_input_writes_empty_file(tmp_path: Path) -> None:
    out = tmp_path / "empty.jsonl"

    rows = export_sft([], out)

    assert rows == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


def test_deterministic_ordering_for_rewards(tmp_path: Path) -> None:
    out = tmp_path / "rewards.jsonl"
    records = [
        _record("task_b", "cand_c", passed=False, score=0.0, duration_ms=3),
        _record("task_a", "cand_b", passed=True, score=1.0, duration_ms=1),
        _record("task_a", "cand_a", passed=True, score=1.0, duration_ms=2),
    ]

    export_rewards(records, out)
    payload = _read_jsonl(out)

    assert [(row["task_id"], row["candidate_id"]) for row in payload] == [
        ("task_a", "cand_a"),
        ("task_a", "cand_b"),
        ("task_b", "cand_c"),
    ]
