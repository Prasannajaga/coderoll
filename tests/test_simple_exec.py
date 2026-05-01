from pathlib import Path

import pytest

from coderoll.config import SandboxConfig
from coderoll.errors import CoderollError
from coderoll.result import CommandResult, ExecutionResult
from coderoll.simple_exec import execute_simple


def _fake_execution_result(stdout: str = "hello\n") -> ExecutionResult:
    command = CommandResult(
        name="run_code",
        command="python solution.py",
        phase="eval",
        exit_code=0,
        stdout=stdout,
        stderr="",
        duration_ms=7,
        timed_out=False,
        result_format="exit_code",
    )
    return ExecutionResult(
        task_id="simple_exec",
        candidate_id="inline",
        exit_code=0,
        stdout=stdout,
        stderr="",
        duration_ms=7,
        timed_out=False,
        error=None,
        sandbox={"type": "docker_cli"},
        language="python",
        image="coderoll-python:3.11",
        phase="complete",
        command_results=[command],
    )


def test_execute_simple_runs_inline_code(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_workspace(self, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        workspace_path = kwargs["workspace_path"]
        source = (workspace_path / "solution.py").read_text(encoding="utf-8")
        assert "print('hi')" in source
        return _fake_execution_result(stdout="hi\n")

    monkeypatch.setattr("coderoll.sandboxes.docker_cli.DockerSandbox.run_workspace", fake_run_workspace)

    result = execute_simple(
        sandbox=SandboxConfig(image="coderoll-python:3.11", timeout=5),
        language="python",
        code="print('hi')\n",
    )

    assert result.stdout == "hi\n"
    assert result.exit_code == 0
    assert captured["image"] == "coderoll-python:3.11"


def test_execute_simple_runs_file_input(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "my_script.py"
    source.write_text("print('from file')\n", encoding="utf-8")

    def fake_run_workspace(self, **kwargs):  # noqa: ANN001
        workspace_path = kwargs["workspace_path"]
        copied = (workspace_path / "solution.py").read_text(encoding="utf-8")
        assert "from file" in copied
        return _fake_execution_result(stdout="from file\n")

    monkeypatch.setattr("coderoll.sandboxes.docker_cli.DockerSandbox.run_workspace", fake_run_workspace)

    result = execute_simple(
        sandbox=SandboxConfig(image="coderoll-python:3.11", timeout=5),
        language="python",
        file=source,
    )

    assert result.stdout == "from file\n"
    assert result.passed is True


def test_execute_simple_requires_exactly_one_input() -> None:
    sandbox = SandboxConfig(image="coderoll-python:3.11", timeout=5)

    with pytest.raises(CoderollError, match="exactly one"):
        execute_simple(sandbox=sandbox)

    with pytest.raises(CoderollError, match="exactly one"):
        execute_simple(sandbox=sandbox, code="print(1)", file="solution.py")
