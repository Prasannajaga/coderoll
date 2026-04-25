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
    assert task.language == "python"
    assert task.image == "coderoll-python:3.11"
    assert task.test_command == "python -m pytest -q --junitxml=.coderoll-results.xml"
    assert task.result_format == "junit"
    assert task.timeout == 5


def test_task_from_dir_js_runtime(tmp_path: Path) -> None:
    task_dir = tmp_path / "js_task"
    task_dir.mkdir()
    (task_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")
    (task_dir / "test_solution.test.js").write_text("// test\n", encoding="utf-8")
    (task_dir / "task.toml").write_text('language = "javascript"\n', encoding="utf-8")

    task = Task.from_dir(task_dir)

    assert task.language == "javascript"
    assert task.image == "coderoll-node:20"
    assert task.entry_file == "solution.js"
    assert task.test_file == "test_solution.test.js"
    assert task.test_command == "node --test --test-reporter=tap"
    assert task.result_format == "tap"


def test_task_from_dir_ts_runtime(tmp_path: Path) -> None:
    task_dir = tmp_path / "ts_task"
    task_dir.mkdir()
    (task_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")
    (task_dir / "test_solution.test.ts").write_text("// test\n", encoding="utf-8")
    (task_dir / "task.toml").write_text('language = "typescript"\n', encoding="utf-8")

    task = Task.from_dir(task_dir)

    assert task.language == "typescript"
    assert task.image == "coderoll-node-ts:20"
    assert task.entry_file == "solution.ts"
    assert task.build_command == "npx tsc --noEmit"
    assert task.test_command == "npm test"
    assert task.result_format == "tap"
