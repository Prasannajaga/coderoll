from pathlib import Path
import builtins
import sys

import pytest

from coderoll.cli import main
import coderoll.cli as cli
from coderoll.config import load_config, load_config_dict
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


def test_init_config_toml_generation(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.toml"
    exit_code = main(["init-config", str(cfg_path)])

    assert exit_code == 0
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert 'id = "file_mode_eval"' in text
    assert 'mode = "file"' in text


def test_init_config_yaml_generation(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.yaml"
    exit_code = main(["init-config", str(cfg_path)])

    assert exit_code == 0
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert "id: file_mode_eval" in text
    assert "mode: file" in text


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
