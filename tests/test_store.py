from pathlib import Path

from coderoll.result import RunRecord
from coderoll.stores.jsonl import JsonlStore, write_records


def _record(candidate_id: str) -> RunRecord:
    return RunRecord(
        run_id=f"run_{candidate_id}",
        created_at="2026-01-01T00:00:00Z",
        task_id="task",
        candidate_id=candidate_id,
        prompt="prompt",
        code="def solution(x): return x",
        code_hash="hash",
        test_hash="testhash",
        passed=False,
        score=0.0,
        exit_code=1,
        stdout="",
        stderr="",
        duration_ms=10,
        timed_out=False,
        error=None,
        sandbox={"type": "docker_cli"},
        metadata={"source": "test"},
    )


def test_jsonl_store_append_and_read(tmp_path: Path) -> None:
    path = tmp_path / "runs" / "records.jsonl"
    store = JsonlStore(path)

    store.append(_record("a"))
    store.append_many([_record("b")])

    records = store.read_all()

    assert len(records) == 2
    assert [record.candidate_id for record in records] == ["a", "b"]


def test_jsonl_store_iter_records(tmp_path: Path) -> None:
    path = tmp_path / "runs" / "records.jsonl"
    store = JsonlStore(path)
    store.append_many([_record("a"), _record("b"), _record("c")])

    candidate_ids = [record.candidate_id for record in store.iter_records()]

    assert candidate_ids == ["a", "b", "c"]


def test_write_records_overwrites_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "runs" / "ranked.jsonl"
    store = JsonlStore(path)
    store.append_many([_record("old_1"), _record("old_2")])

    write_records(path, [_record("new_1")])

    records = JsonlStore(path).read_all()
    assert [record.candidate_id for record in records] == ["new_1"]
