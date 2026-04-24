from pathlib import Path

from coderoll.candidate import Candidate
from coderoll.evaluators.pytest_eval import PytestEvaluator
from coderoll.result import ExecutionResult
from coderoll.runner import Runner
from coderoll.task import Task


class _FakeSandbox:
    def run(self, task: Task, candidate: Candidate) -> ExecutionResult:
        return ExecutionResult(
            task_id=task.id,
            candidate_id=candidate.id,
            exit_code=1,
            stdout=(
                "F                                                                        [100%]\n"
                "FAILED test_solution.py::test_add_one - assert 1 == 2\n"
            ),
            stderr="",
            duration_ms=12,
            timed_out=False,
            error=None,
            sandbox={"type": "fake"},
        )


def _make_task(tmp_path: Path) -> Task:
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    (task_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")
    (task_dir / "test_solution.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    return Task.from_dir(task_dir)


def test_runner_populates_error_from_failed_stdout(tmp_path: Path) -> None:
    task = _make_task(tmp_path)
    runner = Runner(sandbox=_FakeSandbox(), evaluator=PytestEvaluator(), store=None)

    results = runner.run(task, [Candidate.from_string("def solution(x): return x")])

    assert len(results.records) == 1
    record = results.records[0]
    assert record.error == "FAILED test_solution.py::test_add_one - assert 1 == 2"
    assert record.passed is False
