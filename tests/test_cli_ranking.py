from pathlib import Path

import coderoll.cli as cli
from coderoll.config import (
    CandidatesConfig,
    EvalCommandConfig,
    EvalConfig,
    FileConfig,
    OutputConfig,
    RankConfig,
    RunConfig,
    RunnerConfig,
    SandboxConfig,
    SetupConfig,
    ViewerConfig,
)
from coderoll.result import RunRecord, RunResults
from coderoll.stores.jsonl import JsonlStore


def _record(candidate_id: str, score: float, passed: bool) -> RunRecord:
    return RunRecord(
        run_id=f"run_{candidate_id}",
        created_at="2026-01-01T00:00:00Z",
        task_id="cfg",
        candidate_id=candidate_id,
        prompt="prompt",
        code="print('ok')",
        code_hash=f"hash_{candidate_id}",
        test_hash="testhash",
        passed=passed,
        score=score,
        exit_code=0 if passed else 1,
        stdout="",
        stderr="",
        duration_ms=1,
        timed_out=False,
        error=None,
        sandbox={"type": "docker_cli"},
        metadata={},
    )


def _config(
    tmp_path: Path,
    *,
    rank: RankConfig,
    viewer: ViewerConfig,
) -> RunConfig:
    candidates_path = tmp_path / "candidates.jsonl"
    candidates_path.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    return RunConfig(
        id="cfg_eval",
        mode="file",
        language="python",
        project=None,
        file=FileConfig(),
        candidates=CandidatesConfig(path=candidates_path),
        setup=SetupConfig(commands=[]),
        eval=EvalConfig(commands=[EvalCommandConfig(command="python -m pytest")]),
        output=OutputConfig(path=(tmp_path / "runs" / "results.jsonl").resolve()),
        rank=rank,
        runner=RunnerConfig(workers=1),
        sandbox=SandboxConfig(image="coderoll-python:3.11"),
        viewer=viewer,
        raw={},
        base_dir=tmp_path,
    )


def test_cmd_run_from_config_writes_ranked_output_and_uses_ranked_viewer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config(
        tmp_path,
        rank=RankConfig(enabled=True, profile="strict", out=None, top=1),
        viewer=ViewerConfig(enabled=True, out=None, open=False),
    )
    records = [
        _record("a", score=0.1, passed=False),
        _record("b", score=1.0, passed=True),
    ]
    seen_profile: list[str] = []
    viewer_calls: list[tuple[list[str], Path, str | None]] = []
    viewer_input_paths: list[Path] = []

    monkeypatch.setattr(cli, "load_config", lambda _: cfg)
    monkeypatch.setattr(cli, "run_from_config", lambda _: RunResults(records=records))

    def fake_rank_records(items: list[RunRecord], profile: str = "default") -> list[RunRecord]:
        seen_profile.append(profile)
        return list(reversed(items))

    def fake_default_viewer_path(results_path: Path) -> Path:
        viewer_input_paths.append(results_path)
        return tmp_path / "runs" / "viewer.html"

    def fake_write_viewer(items: list[RunRecord], out: Path, title: str | None = None) -> Path:
        viewer_calls.append(([record.candidate_id for record in items], out, title))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("<html></html>", encoding="utf-8")
        return out

    monkeypatch.setattr(cli, "rank_records", fake_rank_records)
    monkeypatch.setattr(cli, "default_viewer_path", fake_default_viewer_path)
    monkeypatch.setattr(cli, "write_viewer", fake_write_viewer)

    cli._cmd_run_from_config(tmp_path / "experiment.toml")

    ranked_path = cfg.output.path.with_name("results.ranked.jsonl")
    ranked_records = JsonlStore(ranked_path).read_all()

    assert seen_profile == ["strict"]
    assert [record.candidate_id for record in ranked_records] == ["b"]
    assert viewer_input_paths == [ranked_path]
    assert viewer_calls[0][0] == ["b"]
    assert viewer_calls[0][1] == (tmp_path / "runs" / "viewer.html")
    assert viewer_calls[0][2] == "coderoll results - ranked by strict"


def test_cmd_run_from_config_skips_ranking_when_disabled_and_uses_raw_viewer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg = _config(
        tmp_path,
        rank=RankConfig(enabled=False, profile="default", out=None, top=None),
        viewer=ViewerConfig(enabled=True, out=None, open=False),
    )
    records = [
        _record("a", score=0.1, passed=False),
        _record("b", score=1.0, passed=True),
    ]
    viewer_calls: list[tuple[list[str], Path, str | None]] = []
    viewer_input_paths: list[Path] = []

    monkeypatch.setattr(cli, "load_config", lambda _: cfg)
    monkeypatch.setattr(cli, "run_from_config", lambda _: RunResults(records=records))
    monkeypatch.setattr(
        cli,
        "rank_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rank_records should not run")),
    )

    def fake_default_viewer_path(results_path: Path) -> Path:
        viewer_input_paths.append(results_path)
        return tmp_path / "runs" / "viewer.html"

    def fake_write_viewer(items: list[RunRecord], out: Path, title: str | None = None) -> Path:
        viewer_calls.append(([record.candidate_id for record in items], out, title))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("<html></html>", encoding="utf-8")
        return out

    monkeypatch.setattr(cli, "default_viewer_path", fake_default_viewer_path)
    monkeypatch.setattr(cli, "write_viewer", fake_write_viewer)

    cli._cmd_run_from_config(tmp_path / "experiment.toml")

    ranked_path = cfg.output.path.with_name("results.ranked.jsonl")
    assert not ranked_path.exists()
    assert viewer_input_paths == [cfg.output.path]
    assert viewer_calls[0][0] == ["a", "b"]
    assert viewer_calls[0][2] == "coderoll run: cfg_eval"


def test_cmd_rank_out_writes_ranked_jsonl_without_modifying_input(tmp_path: Path) -> None:
    raw_path = tmp_path / "runs" / "results.jsonl"
    out_path = tmp_path / "runs" / "strict_ranked.jsonl"
    JsonlStore(raw_path).append_many(
        [
            _record("fail_high", score=0.9, passed=False),
            _record("pass_low", score=0.1, passed=True),
            _record("pass_high", score=0.8, passed=True),
        ]
    )
    raw_before = raw_path.read_text(encoding="utf-8")

    cli._cmd_rank(
        results_path=raw_path,
        top=None,
        profile="strict",
        out_path=out_path,
        show_reason=False,
        group_by=None,
        show_code=False,
        only_failed=False,
        only_passed=False,
    )

    ranked_records = JsonlStore(out_path).read_all()

    assert [record.candidate_id for record in ranked_records] == ["pass_high", "pass_low", "fail_high"]
    assert raw_path.read_text(encoding="utf-8") == raw_before


def test_cmd_rank_without_out_prints_summary(capsys, tmp_path: Path) -> None:
    raw_path = tmp_path / "runs" / "results.jsonl"
    JsonlStore(raw_path).append_many(
        [
            _record("a", score=0.0, passed=False),
            _record("b", score=1.0, passed=True),
        ]
    )

    cli._cmd_rank(
        results_path=raw_path,
        top=None,
        profile="default",
        out_path=None,
        show_reason=False,
        group_by=None,
        show_code=False,
        only_failed=False,
        only_passed=False,
    )

    captured = capsys.readouterr()
    assert "1. candidate_id=b" in captured.out


def test_cmd_run_from_config_writes_events_jsonl(tmp_path: Path, monkeypatch) -> None:
    cfg = _config(
        tmp_path,
        rank=RankConfig(enabled=False, profile="default", out=None, top=None),
        viewer=ViewerConfig(enabled=False, out=None, open=False),
    )
    records = [_record("a", score=0.1, passed=False)]

    monkeypatch.setattr(cli, "load_config", lambda _: cfg)
    monkeypatch.setattr(cli, "run_from_config", lambda _: RunResults(records=records))

    cli._cmd_run_from_config(tmp_path / "experiment.toml")

    run_dirs = [path for path in (tmp_path / "runs").iterdir() if path.is_dir() and path.name.startswith("run_")]
    assert len(run_dirs) == 1
    events_path = run_dirs[0] / "events.jsonl"
    assert events_path.exists()
