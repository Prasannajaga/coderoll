from pathlib import Path

from coderoll.config import (
    EvalConfig,
    EvalCommandConfig,
    FileConfig,
    OutputConfig,
    ProjectConfig,
    RankConfig,
    RunConfig,
    RunnerConfig,
    SandboxConfig,
    SetupConfig,
    ViewerConfig,
)
from coderoll.runner import run_from_config


def main() -> None:
    # Resolve all relative paths from the repository root so this script is
    # stable no matter where it is called from.
    base_dir = Path(".").resolve()

    # Build a RunConfig completely in Python (no TOML/YAML file needed).
    # This example uses PROJECT mode, where Coderoll evaluates an entire
    # project directory instead of reading candidate solutions from a JSONL.
    config = RunConfig(
        id="sdk_project_mode_eval",
        mode="project",
        language="python",
        # Project mode input: the folder that contains multiple candidate
        # solutions/files. include/exclude control which files are considered.
        project=ProjectConfig(
            path=Path("example/python/project/simple"),
            include=["**/*"],
            exclude=[".git/**", "__pycache__/**", ".coderoll/**"],
        ),
        # File naming convention inside each candidate project entry.
        file=FileConfig(
            code_file="solution.py",
            test_file="test_solution.py",
        ),
        # In project mode, candidates are discovered from project.path,
        # so candidates config must be None.
        candidates=None,
        # Optional setup commands executed before evaluation commands.
        setup=SetupConfig(
            commands=[],
        ),
        # Evaluation commands that produce scores/signals.
        eval=EvalConfig(
            commands=[
                EvalCommandConfig(
                    name="tests",
                    # Run pytest quietly and export JUnit XML for parsing.
                    command="python -m pytest -q test_solution.py --junitxml=.coderoll-results.xml",
                    result_format="junit",
                )
            ],
            stop_on_first_failure=False,
            score_strategy="weighted",
        ),
        # Raw run output written as JSONL.
        output=OutputConfig(path=Path("runs/sdk_project_mode_results.jsonl")),
        # Ranking turns raw eval results into sorted candidate results.
        rank=RankConfig(
            enabled=True,
            profile="default",
            out=None,
            top=None,
        ),
        # Run multiple candidates in parallel workers.
        runner=RunnerConfig(workers=2),
        # Container limits/sandboxing for deterministic and safe execution.
        sandbox=SandboxConfig(
            image="coderoll-python:3.11",
            timeout=10,
            memory="512m",
            cpus="1",
            pids_limit=128,
            network=False,
        ),
        # Optional HTML viewer for quick inspection of run results.
        viewer=ViewerConfig(
            enabled=True,
            out="runs/sdk_project_mode_results.viewer.html",
            open=False,
        ),
        raw={},
        base_dir=base_dir,
    )

    # Execute the configured run and print a short summary.
    results = run_from_config(config)
    print("summary:", results.summary())
    print("output:", config.output_path)


if __name__ == "__main__":
    main()
