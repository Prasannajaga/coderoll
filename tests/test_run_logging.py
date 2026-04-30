import json
from pathlib import Path

from coderoll.run_logging import EventLogger, RunStage, StageReporter


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rows.append(json.loads(line))
    return rows


def test_event_logger_writes_valid_jsonl(tmp_path: Path) -> None:
    logger = EventLogger(run_dir=tmp_path / "runs" / "run_x", run_id="run_x")
    logger.emit(RunStage.CREATING_SANDBOX, "Creating sandbox")

    events_path = tmp_path / "runs" / "run_x" / "events.jsonl"
    assert events_path.exists()
    rows = _read_jsonl(events_path)
    assert len(rows) == 1
    assert rows[0]["stage"] == "creating_sandbox"
    assert rows[0]["run_id"] == "run_x"
    assert rows[0]["data"] == {}


def test_stage_reporter_prints_expected_output(capsys, tmp_path: Path) -> None:
    logger = EventLogger(run_dir=tmp_path / "runs" / "run_y", run_id="run_y")
    reporter = StageReporter(logger, total_steps=5)

    reporter.step(1, RunStage.CREATING_SANDBOX, "Creating sandbox")
    reporter.step(2, RunStage.EXECUTING_SANDBOX, "Executing sandbox")
    reporter.step(3, RunStage.SANDBOX_EXECUTION_COMPLETE, "Sandbox execution complete")
    reporter.step(4, RunStage.RANKING_RESULTS, "Ranking results")
    reporter.step(5, RunStage.EXPORTING_RESULTS, "Exporting results")
    reporter.done()

    captured = capsys.readouterr()
    assert captured.out == (
        "[1/5] Creating sandbox...\n"
        "[2/5] Executing sandbox...\n"
        "[3/5] Sandbox execution complete\n"
        "[4/5] Ranking results...\n"
        "[5/5] Exporting results...\n"
        "\n"
        "DONE\n"
    )


def test_stage_reporter_failed_emits_error_event(capsys, tmp_path: Path) -> None:
    logger = EventLogger(run_dir=tmp_path / "runs" / "run_z", run_id="run_z")
    reporter = StageReporter(logger, total_steps=5)

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        reporter.failed("Run failed", exc)

    captured = capsys.readouterr()
    assert "FAILED: Run failed" in captured.out

    events_path = tmp_path / "runs" / "run_z" / "events.jsonl"
    rows = _read_jsonl(events_path)
    assert rows[-1]["stage"] == "failed"
    assert rows[-1]["level"] == "error"
    assert rows[-1]["data"]["error_type"] == "RuntimeError"
    assert rows[-1]["data"]["error"] == "boom"
