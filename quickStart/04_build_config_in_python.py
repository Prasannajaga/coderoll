from pathlib import Path

from coderoll.config import (
    CandidatesConfig,
    EvalConfig,
    FileConfig,
    OutputConfig,
    RunConfig,
    RunnerConfig,
    SandboxConfig,
    SetupConfig,
    ViewerConfig,
)
from coderoll.runner import run_from_config


def main() -> None:
    config = RunConfig(
        id="sdk_file_mode_eval",
        mode="file",
        language="python",
        project=None,
        file=FileConfig(
            code_file="solution.py",
            test_file="test_solution.py",
        ),
        candidates=CandidatesConfig(
            path=Path("examples/file_mode/candidates.jsonl"),
            type="jsonl",
        ),
        setup=SetupConfig(commands=[]),
        eval=EvalConfig(commands=[]),
        output=OutputConfig(path=Path("runs/sdk_file_mode_results.jsonl")),
        runner=RunnerConfig(workers=2),
        sandbox=SandboxConfig(
            image="coderoll-python:3.11",
            timeout=10,
            memory="512m",
            cpus="1",
            pids_limit=128,
            network=False,
        ),
        viewer=ViewerConfig(enabled=False),
        raw={},
        base_dir=Path(".").resolve(),
    )

    # Because this config is created directly, include the default Python eval command.
    # Loading YAML with language: python fills this automatically.
    config.eval.commands = load_python_eval_commands()

    results = run_from_config(config)
    print("summary:", results.summary())
    print("output:", config.output_path)


def load_python_eval_commands():
    from coderoll.config import EvalCommandConfig

    return [
        EvalCommandConfig(
            name="tests",
            command="python -m pytest -q --junitxml=.coderoll-results.xml",
            result_format="junit",
        )
    ]


if __name__ == "__main__":
    main()
