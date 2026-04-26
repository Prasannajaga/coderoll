from pathlib import Path
import builtins
import sys

import pytest

from coderoll.cli import main
import coderoll.cli as cli
from coderoll.config import load_config, load_config_dict
from coderoll.errors import CoderollError


def _setup_task_files(root: Path) -> None:
    task_dir = root / "examples" / "add_one"
    task_dir.mkdir(parents=True)
    (task_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")
    (task_dir / "test_solution.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    candidates = task_dir / "candidates.jsonl"
    candidates.write_text('{"code": "def solution(x): return x"}\n', encoding="utf-8")


def test_load_toml_config(tmp_path: Path) -> None:
    _setup_task_files(tmp_path)
    cfg_path = tmp_path / "coderoll.toml"
    cfg_path.write_text(
        'id = "add_one_eval"\n\n'
        "[task]\n"
        'path = "examples/add_one"\n\n'
        "[candidates]\n"
        'path = "examples/add_one/candidates.jsonl"\n\n'
        "[output]\n"
        'path = "runs/add_one.jsonl"\n\n'
        "[runner]\n"
        "workers = 2\n\n"
        "[viewer]\n"
        "enabled = true\n"
        "open = false\n",
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.id == "add_one_eval"
    assert cfg.task_path == (tmp_path / "examples" / "add_one").resolve()
    assert cfg.candidates_path == (tmp_path / "examples" / "add_one" / "candidates.jsonl").resolve()
    assert cfg.output_path == (tmp_path / "runs" / "add_one.jsonl").resolve()
    assert cfg.runner.workers == 2
    assert cfg.viewer.enabled is True
    assert cfg.viewer.open is False


def test_load_config_missing_required_field(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.toml"
    cfg_path.write_text(
        "[task]\n"
        'path = "examples/add_one"\n\n'
        "[candidates]\n"
        'path = "examples/add_one/candidates.jsonl"\n\n'
        "[output]\n"
        'path = "runs/add_one.jsonl"\n',
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="id is required"):
        load_config(cfg_path)


def test_load_config_relative_path_resolution(tmp_path: Path) -> None:
    _setup_task_files(tmp_path)
    cfg_dir = tmp_path / "configs"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "coderoll.toml"
    cfg_path.write_text(
        'id = "add_one_eval"\n\n'
        "[task]\n"
        'path = "../examples/add_one"\n\n'
        "[candidates]\n"
        'path = "../examples/add_one/candidates.jsonl"\n\n'
        "[output]\n"
        'path = "../runs/add_one.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.task_path == (tmp_path / "examples" / "add_one").resolve()
    assert cfg.output_path == (tmp_path / "runs" / "add_one.jsonl").resolve()


def test_load_config_invalid_workers(tmp_path: Path) -> None:
    _setup_task_files(tmp_path)
    cfg_path = tmp_path / "coderoll.toml"
    cfg_path.write_text(
        'id = "add_one_eval"\n\n'
        "[task]\n"
        'path = "examples/add_one"\n\n'
        "[candidates]\n"
        'path = "examples/add_one/candidates.jsonl"\n\n'
        "[output]\n"
        'path = "runs/add_one.jsonl"\n\n'
        "[runner]\n"
        "workers = 0\n",
        encoding="utf-8",
    )

    with pytest.raises(CoderollError, match="runner.workers must be an integer >= 1"):
        load_config(cfg_path)


def test_load_new_workspace_config_relative_paths(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text('{"files":{"solution.py":"x = 1"}}\n', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "project_eval"\n\n'
        "[workspace]\n"
        'mode = "project"\n'
        'path = "project"\n\n'
        "[candidates]\n"
        'type = "jsonl"\n'
        'path = "candidates.jsonl"\n'
        'mode = "files"\n\n'
        "[[eval.commands]]\n"
        'name = "tests"\n'
        'command = "python -m pytest"\n'
        'result_format = "junit"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.workspace.mode == "project"
    assert cfg.workspace.path == project.resolve()
    assert cfg.candidates.type == "jsonl"
    assert cfg.candidates.mode == "files"
    assert cfg.eval.commands[0].name == "tests"
    assert cfg.eval.commands[0].result_format == "junit"
    assert cfg.output_path == (tmp_path / "runs" / "results.jsonl").resolve()


def test_load_new_config_setup_and_simple_eval_commands(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    candidates = tmp_path / "candidate.json"
    candidates.write_text('{"code":"x = 1"}', encoding="utf-8")
    cfg_path = tmp_path / "experiment.toml"
    cfg_path.write_text(
        'id = "single_eval"\n\n'
        "[workspace]\n"
        'mode = "project"\n'
        'path = "project"\n\n'
        "[candidates]\n"
        'type = "json"\n'
        'path = "candidate.json"\n'
        'mode = "file"\n'
        'entry_file = "solution.py"\n\n'
        "[setup]\n"
        'commands = ["python -m pip install -r requirements.txt"]\n'
        "allow_candidate_dependencies = true\n\n"
        "[eval]\n"
        'commands = ["python -m pytest"]\n'
        'result_format = "exit_code"\n\n'
        "[output]\n"
        'path = "runs/results.jsonl"\n',
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.setup.commands == ["python -m pip install -r requirements.txt"]
    assert cfg.setup.allow_candidate_dependencies is True
    assert cfg.eval.commands[0].command == "python -m pytest"
    assert cfg.candidates.entry_file == "solution.py"


def test_init_config_toml_generation(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.toml"
    exit_code = main(["init-config", str(cfg_path)])

    assert exit_code == 0
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert 'id = "add_one_eval"' in text
    assert "[task]" in text


def test_init_config_yaml_generation(tmp_path: Path) -> None:
    cfg_path = tmp_path / "coderoll.yaml"
    exit_code = main(["init-config", str(cfg_path)])

    assert exit_code == 0
    assert cfg_path.exists()
    text = cfg_path.read_text(encoding="utf-8")
    assert "id: add_one_eval" in text
    assert "task:" in text


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
