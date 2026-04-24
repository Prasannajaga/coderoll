from pathlib import Path

from coderoll.result import RunRecord
from coderoll.viewer import default_viewer_path, render_html, write_viewer


def _record(candidate_id: str = "cand_1") -> RunRecord:
    return RunRecord(
        run_id="run_1",
        created_at="2026-01-01T00:00:00Z",
        task_id="add_one",
        candidate_id=candidate_id,
        prompt="Write solution",
        code="def solution(x): return x + 1",
        code_hash="abc",
        test_hash="def",
        passed=True,
        score=1.0,
        exit_code=0,
        stdout="1 passed",
        stderr="",
        duration_ms=10,
        timed_out=False,
        error=None,
        sandbox={"type": "docker_cli"},
        metadata={"source": "test"},
    )


def test_default_viewer_path() -> None:
    assert default_viewer_path("runs/add_one.jsonl") == Path("runs/add_one.viewer.html")


def test_render_html_contains_expected_sections() -> None:
    html = render_html([_record()], title="My Report")

    assert "My Report" in html
    assert "total candidates" in html
    assert "status-filter" in html
    assert "candidate_id" in html
    assert "Export filtered JSON" in html
    assert "Raw JSON" in html


def test_write_viewer_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "report.html"
    written = write_viewer([_record("cand_x")], out, title="X")

    assert written == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "cand_x" in content
    assert "<html" in content
