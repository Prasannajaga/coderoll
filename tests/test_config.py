from pathlib import Path
import builtins
import sys

import pytest

from coderoll.cli import main
import coderoll.cli as cli
from coderoll.config import default_ranked_path, load_config, load_config_dict
from coderoll.errors import CoderollError


def test_project_mode_config_loads(tmp_path: Path) -> None:
    project = tmp_path / "generated_project"
    project.mkdir()
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "project_eval"\n'
        'mode = "project"\n\n'
        "[project]\n"
        'path = "generated_project"\n\n'
        "[[eval.commands]]\n"
        'name = "tests"\n'
        'command = "python -m pytest"\n'
        'result_format = "junit"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n\n'
        "[runner]\n"
        "workers = 2\n",
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.id == "project_eval"
    assert cfg.mode == "project"
    assert cfg.project is not None
    assert cfg.project.path == project.resolve()
    assert cfg.candidates is None
    assert cfg.output_path == (tmp_path / "runs" / "results.jsonl").resolve()
    assert cfg.runner.workers == 2
    assert cfg.eval.commands[0].result_format == "junit"


def test_file_mode_config_loads(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n'
        'type = "jsonl"\n\n'
        "[file]\n"
        'code_file = "src/solution.py"\n'
        'test_file = "tests/test_solution.py"\n\n'
        "[setup]\n"
        'commands = ["python -m pip install -r requirements.txt"]\n\n'
        "[eval]\n"
        'commands = ["python -m pytest"]\n'
        'result_format = "exit_code"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.mode == "file"
    assert cfg.project is None
    assert cfg.candidates is not None
    assert cfg.candidates.path == candidates.resolve()
    assert cfg.candidates.type == "jsonl"
    assert cfg.file.code_file == "src/solution.py"
    assert cfg.file.test_file == "tests/test_solution.py"
    assert cfg.setup.commands == ["python -m pip install -r requirements.txt"]
    assert cfg.eval.commands[0].command == "python -m pytest"


def test_language_preset_supplies_file_sandbox_and_eval_defaults(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"code":"module.exports = {}"}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "js_eval"\n'
        'mode = "file"\n'
        'language = "javascript"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.language == "javascript"
    assert cfg.file.code_file == "solution.js"
    assert cfg.file.test_file == "test_solution.test.js"
    assert cfg.sandbox.image == "coderoll-node:20"
    assert len(cfg.eval.commands) == 1
    assert cfg.eval.commands[0].command == "node --test --test-reporter=tap"
    assert cfg.eval.commands[0].result_format == "tap"


@pytest.mark.parametrize(
    ("language", "code_file", "test_file", "image", "command", "result_format"),
    [
        ("go", "solution.go", "solution_test.go", "coderoll-go:1.26", "GO111MODULE=off go test ./...", "exit_code"),
        ("java", "Solution.java", "TestSolution.java", "coderoll-java:21", "javac *.java && java -ea TestSolution", "exit_code"),
        (
            "rust",
            "solution.rs",
            "test_solution.rs",
            "coderoll-rust:1",
            "rustc --test test_solution.rs -o .coderoll-tests && ./.coderoll-tests",
            "exit_code",
        ),
    ],
)
def test_language_presets_for_go_java_rust(
    tmp_path: Path,
    language: str,
    code_file: str,
    test_file: str,
    image: str,
    command: str,
    result_format: str,
) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"code":"placeholder"}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        f'id = "{language}_eval"\n'
        'mode = "file"\n'
        f'language = "{language}"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.language == language
    assert cfg.file.code_file == code_file
    assert cfg.file.test_file == test_file
    assert cfg.sandbox.image == image
    assert len(cfg.eval.commands) == 1
    assert cfg.eval.commands[0].command == command
    assert cfg.eval.commands[0].result_format == result_format


def test_typescript_language_preset_includes_typecheck_and_tests(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "ts_eval"\n'
        'mode = "project"\n'
        'language = "typescript"\n\n'
        "[project]\n"
        'path = "project"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.sandbox.image == "coderoll-node-ts:20"
    assert [(cmd.name, cmd.command, cmd.result_format) for cmd in cfg.eval.commands] == [
        ("typecheck", "tsc --noEmit", "exit_code"),
        ("tests", "npm test", "tap"),
    ]


def test_mode_is_required(tmp_path: Path) -> None:
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "missing_mode"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="mode is required"):
        load_config(cfg_path)


def test_invalid_mode_rejected(tmp_path: Path) -> None:
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "bad_mode"\n'
        'mode = "overlay"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="mode must be one of"):
        load_config(cfg_path)


def test_project_path_required_for_project_mode(tmp_path: Path) -> None:
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "project_eval"\n'
        'mode = "project"\n\n'
        "[project]\n\n"
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="project.path is required"):
        load_config(cfg_path)


def test_candidates_path_required_for_file_mode(tmp_path: Path) -> None:
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n\n"
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="candidates.path is required"):
        load_config(cfg_path)


def test_relative_paths_resolve_from_config_location(tmp_path: Path) -> None:
    project = tmp_path / "generated_project"
    project.mkdir()
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "experiment.toml"
    cfg_path.write_text(
        'id = "project_eval"\n'
        'mode = "project"\n\n'
        "[project]\n"
        'path = "../generated_project"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "../runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.project is not None
    assert cfg.project.path == project.resolve()
    assert cfg.output_path == (tmp_path / "runs" / "results.jsonl").resolve()


def test_default_ranked_path_jsonl_suffix() -> None:
    assert default_ranked_path("runs/results.jsonl") == Path("runs/results.ranked.jsonl")


def test_default_ranked_path_non_jsonl_suffix() -> None:
    assert default_ranked_path("runs/results.ndjson") == Path("runs/results.ndjson.ranked.jsonl")


def test_default_ranked_path_no_suffix() -> None:
    assert default_ranked_path("runs/results") == Path("runs/results.ranked.jsonl")


def test_load_config_invalid_workers(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n\n'
        "[runner]\n"
        "workers = 0\n",
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="runner.workers must be an integer >= 1"):
        load_config(cfg_path)


def test_rank_defaults_when_section_missing(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.rank.enabled is True
    assert cfg.rank.profile == "default"
    assert cfg.rank.out is None
    assert cfg.rank.top is None


def test_rank_invalid_profile_rejected(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n\n'
        "[rank]\n"
        'profile = "fast"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="rank.profile must be one of: default, strict, debug"):
        load_config(cfg_path)


def test_rank_invalid_top_rejected(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n\n'
        "[rank]\n"
        "top = 0\n",
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="rank.top must be a positive integer"):
        load_config(cfg_path)


def test_rank_out_resolves_from_config_dir(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "../candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "../runs/results.jsonl"\n\n'
        "[rank]\n"
        'out = "../runs/strict_ranked.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.rank.out == (tmp_path / "runs" / "strict_ranked.jsonl").resolve()


def test_sandbox_cpus_nested_quotes_are_normalized(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n\n'
        "[sandbox]\n"
        'cpus = "\\"1\\""\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.sandbox.cpus == "1"


def test_sandbox_cpus_invalid_value_rejected(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "file_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "candidates.jsonl"\n\n'
        "[[eval.commands]]\n"
        'command = "python -m pytest"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n\n'
        "[sandbox]\n"
        'cpus = "abc"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="sandbox.cpus must be a positive rational value"):
        load_config(cfg_path)


def test_init_config_toml_generation(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.toml"
    exit_code = main(["init-config", str(cfg_path)])

    assert exit_code == 0
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert 'id = "file_mode_eval"' in text
    assert 'mode = "file"' in text
    assert "[rank]" in text
    assert 'profile = "default"' in text


def test_init_config_yaml_generation(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.yaml"
    exit_code = main(["init-config", str(cfg_path)])

    assert exit_code == 0
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert "id: file_mode_eval" in text
    assert "mode: file" in text
    assert "rank:" in text
    assert "profile: default" in text


def test_yaml_missing_dependency_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "coderoll.yaml"
    cfg_path.write_text("id: test\n", encoding="utf-8")

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "yaml":
            raise ModuleNotFoundError("No module named 'yaml'")
        return original_import(name, globals, locals, fromlist, level)

    sys.modules.pop("yaml", None)
    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(
        CoderollError,
        match="YAML config requires PyYAML. Install with: pip install 'coderoll\\[yaml\\]'",
    ):
        load_config_dict(cfg_path)


def test_run_positional_config_detection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_path = tmp_path / "coderoll.toml"
    cfg_path.write_text('id = "x"\n', encoding="utf-8")
    seen: list[Path] = []

    def fake_run_from_config(path: Path) -> None:
        seen.append(path)

    monkeypatch.setattr(cli, "_cmd_run_from_config", fake_run_from_config)

    exit_code = main(["run", str(cfg_path)])

    assert exit_code == 0
    assert seen == [cfg_path]


def test_run_rejects_positional_config_with_config_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_path = tmp_path / "coderoll.toml"
    other_path = tmp_path / "other.toml"
    cfg_path.write_text('id = "x"\n', encoding="utf-8")
    other_path.write_text('id = "y"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "_cmd_run_from_config", lambda path: None)

    exit_code = main(["run", str(cfg_path), "--config", str(other_path)])

    assert exit_code == 1


def test_run_single_candidate_uses_task_entry_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    candidate_path = tmp_path / "candidate.go"
    candidate_path.write_text("package main\n", encoding="utf-8")
    out_path = tmp_path / "runs" / "results.jsonl"

    class FakeTask:
        id = "go_task"
        entry_file = "solution.go"
        timeout = 5

    class FakeResults:
        records: list[object] = []

        def summary(self) -> dict[str, object]:
            return {"total": 0, "passed": 0, "failed": 0, "best_score": 0.0}

    class FakeRunner:
        def __init__(self, sandbox, evaluator, store) -> None:  # noqa: ANN001
            self.sandbox = sandbox
            self.evaluator = evaluator
            self.store = store

        def run(self, task, candidates, workers):  # noqa: ANN001
            return FakeResults()

    captured: dict[str, object] = {}

    def fake_from_file(path: Path, entry_file: str | None = None):  # noqa: ANN202
        captured["path"] = path
        captured["entry_file"] = entry_file
        return object()

    monkeypatch.setattr(cli.Task, "from_dir", lambda path: FakeTask())
    monkeypatch.setattr(cli.Candidate, "from_file", fake_from_file)
    monkeypatch.setattr(cli, "Runner", FakeRunner)

    exit_code = main(
        [
            "run",
            str(task_dir),
            "--candidate",
            str(candidate_path),
            "--out",
            str(out_path),
        ]
    )

    assert exit_code == 0
    assert captured["path"] == candidate_path
    assert captured["entry_file"] == "solution.go"
