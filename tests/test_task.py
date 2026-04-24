from pathlib import Path

from coderoll.task import Task


def test_task_from_dir_with_toml(tmp_path: Path) -> None:
    task_dir = tmp_path / "my_task"
    task_dir.mkdir()
    (task_dir / "prompt.txt").write_text("Solve it\n", encoding="utf-8")
    (task_dir / "tests_custom.py").write_text("def test_ok():\n    assert 1 == 1\n", encoding="utf-8")
    (task_dir / "task.toml").write_text(
        'id = "custom"\n'
        'entry_file = "answer.py"\n'
        'test_file = "tests_custom.py"\n'
        'test_command = "python -m pytest -q"\n'
        "timeout = 7\n",
        encoding="utf-8",
    )

    task = Task.from_dir(task_dir)

    assert task.id == "custom"
    assert task.entry_file == "answer.py"
    assert task.test_file == "tests_custom.py"
    assert task.timeout == 7


def test_task_from_dir_without_toml_uses_defaults(tmp_path: Path) -> None:
    task_dir = tmp_path / "simple"
    task_dir.mkdir()
    (task_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")
    (task_dir / "test_solution.py").write_text(
        "def test_smoke():\n    assert True\n", encoding="utf-8"
    )

    task = Task.from_dir(task_dir)

    assert task.id == "simple"
    assert task.entry_file == "solution.py"
    assert task.test_file == "test_solution.py"
    assert task.timeout == 5
