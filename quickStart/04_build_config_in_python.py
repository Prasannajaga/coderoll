from pathlib import Path

from coderoll.config import (
    CandidatesConfig,
    EvalConfig,
    EvalCommandConfig,
    FileConfig,
    OutputConfig,
    RankConfig,
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
            path=Path("example/python/project/simple/candidates_100.jsonl"),
            type="jsonl",
        ),
        setup=SetupConfig(
            commands=[],
        ),
        eval=EvalConfig(
            commands=[
                EvalCommandConfig(
                    name="tests",
                    command="python -m pytest -q test_solution.py --junitxml=.coderoll-results.xml",
                    result_format="junit",
                )
            ],
            stop_on_first_failure=False,
            score_strategy="weighted",
        ),
        output=OutputConfig(path=Path("runs/sdk_file_mode_results.jsonl")),
        rank=RankConfig(
            enabled=True,
            profile="default",
            out=None,
            top=None,
        ),
        runner=RunnerConfig(workers=2),
        sandbox=SandboxConfig(
            image="coderoll-python:3.11",
            timeout=10,
            memory="512m",
            cpus="1",
            pids_limit=128,
            network=False,
        ),
        viewer=ViewerConfig(
            enabled=True,
            out="runs/sdk_file_mode_results.viewer.html",
            open=False,
        ),
        raw={},
        base_dir=Path(".").resolve(),
    )

    results = run_from_config(config)
    print("summary:", results.summary())
    print("output:", config.output_path)


if __name__ == "__main__":
    main()
