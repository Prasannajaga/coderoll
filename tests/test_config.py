from pathlib import Path
import builtins
import sys

import pytest

from coderoll.cli import main
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
