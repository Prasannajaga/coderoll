from pathlib import Path
from typing import Any
import json

from .result import RunRecord


def export_sft(
    records: list[RunRecord],
    out_path: str | Path,
    include_metadata: bool = False,
) -> int:
    by_task: dict[str, list[RunRecord]] = {}
    for record in records:
        by_task.setdefault(record.task_id, []).append(record)

    rows: list[dict[str, Any]] = []
    for task_id in sorted(by_task):
        passed_records = [record for record in by_task[task_id] if record.passed]
        if not passed_records:
            continue
        best = min(
            passed_records,
            key=lambda record: (-record.score, record.duration_ms, record.candidate_id),
        )
        row: dict[str, Any] = {
            "prompt": best.prompt,
            "completion": best.code,
            "task_id": best.task_id,
            "candidate_id": best.candidate_id,
            "score": best.score,
        }
        if include_metadata:
            row["metadata"] = {
                "passed": best.passed,
                "duration_ms": best.duration_ms,
                "code_hash": best.code_hash,
                "test_hash": best.test_hash,
                "created_at": best.created_at,
                "language": best.language,
                "phase": best.phase,
                "tests_total": best.tests_total,
                "tests_passed": best.tests_passed,
                "build_passed": best.build_passed,
                "score_details": best.score_details or {},
            }
        rows.append(row)

    _write_jsonl(rows, out_path)
    return len(rows)


def export_preferences(
    records: list[RunRecord],
    out_path: str | Path,
    include_metadata: bool = False,
) -> int:
    by_task: dict[str, list[RunRecord]] = {}
    for record in records:
        by_task.setdefault(record.task_id, []).append(record)

    rows: list[dict[str, Any]] = []
    for task_id in sorted(by_task):
        task_records = by_task[task_id]
        passed_records = [record for record in task_records if record.passed]
        failed_records = [record for record in task_records if not record.passed]
        if not passed_records or not failed_records:
            continue

        chosen = min(
            passed_records,
            key=lambda record: (-record.score, record.duration_ms, record.candidate_id),
        )
        rejected = min(
            failed_records,
            key=lambda record: (record.score, -record.duration_ms, record.candidate_id),
        )

        row = {
            "prompt": chosen.prompt,
            "chosen": chosen.code,
            "rejected": rejected.code,
            "task_id": chosen.task_id,
            "chosen_id": chosen.candidate_id,
            "rejected_id": rejected.candidate_id,
            "chosen_score": chosen.score,
            "rejected_score": rejected.score,
        }
        if include_metadata:
            row["metadata"] = {
                "chosen_duration_ms": chosen.duration_ms,
                "rejected_duration_ms": rejected.duration_ms,
                "chosen_code_hash": chosen.code_hash,
                "rejected_code_hash": rejected.code_hash,
                "test_hash": chosen.test_hash,
                "language": chosen.language,
                "chosen_phase": chosen.phase,
                "rejected_phase": rejected.phase,
                "chosen_tests_total": chosen.tests_total,
                "chosen_tests_passed": chosen.tests_passed,
                "rejected_tests_total": rejected.tests_total,
                "rejected_tests_passed": rejected.tests_passed,
                "chosen_build_passed": chosen.build_passed,
                "rejected_build_passed": rejected.build_passed,
                "chosen_score_details": chosen.score_details or {},
                "rejected_score_details": rejected.score_details or {},
            }
        rows.append(row)

    _write_jsonl(rows, out_path)
    return len(rows)


def export_rewards(
    records: list[RunRecord],
    out_path: str | Path,
    include_metadata: bool = False,
) -> int:
    ordered = sorted(records, key=lambda record: (record.task_id, record.candidate_id))
    rows: list[dict[str, Any]] = []
    for record in ordered:
        row: dict[str, Any] = {
            "prompt": record.prompt,
            "completion": record.code,
            "reward": record.score,
            "task_id": record.task_id,
            "candidate_id": record.candidate_id,
            "passed": record.passed,
            "score": record.score,
        }
        if include_metadata:
            row["metadata"] = {
                "duration_ms": record.duration_ms,
                "exit_code": record.exit_code,
                "timed_out": record.timed_out,
                "error": record.error,
                "code_hash": record.code_hash,
                "test_hash": record.test_hash,
                "created_at": record.created_at,
                "language": record.language,
                "phase": record.phase,
                "tests_total": record.tests_total,
                "tests_passed": record.tests_passed,
                "build_passed": record.build_passed,
                "score_details": record.score_details or {},
            }
        rows.append(row)

    _write_jsonl(rows, out_path)
    return len(rows)


def _write_jsonl(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
