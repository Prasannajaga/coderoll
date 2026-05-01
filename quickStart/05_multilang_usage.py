from __future__ import annotations

import argparse
from pathlib import Path

from coderoll.config import (
    EvalCommandConfig,
    EvalConfig,
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


LANGUAGE_SETTINGS = {
    "python": {
        "project_path": Path("example/python/project/simple/generated_project"),
        "code_file": "solution.py",
        "test_file": "test_solution.py",
        "test_command": "python -m pytest -q --junitxml=.coderoll-results.xml",
        "result_format": "junit",
        "image": "coderoll-python:3.11",
    },
    "javascript": {
        "project_path": Path("example/js/project/simple/generated_project"),
        "code_file": "solution.js",
        "test_file": "test_solution.test.js",
        "test_command": "npm test -- --reporter tap",
        "result_format": "tap",
        "image": "coderoll-javascript:latest",
    },
    "typescript": {
        "project_path": Path("example/ts/project/simple/generated_project"),
        "code_file": "solution.ts",
        "test_file": "test_solution.test.ts",
        "test_command": "npm test -- --reporter tap",
        "result_format": "tap",
        "image": "coderoll-typescript:latest",
    },
    "go": {
        "project_path": None,
        "code_file": "solution.go",
        "test_file": "solution_test.go",
        "test_command": "go test -json ./...",
        "result_format": "tap",
        "image": "coderoll-go:latest",
    },
}


def build_run_config(language: str, workers: int) -> RunConfig | None:
    settings = LANGUAGE_SETTINGS[language]
    project_path = settings["project_path"]
    if project_path is None or not project_path.exists():
        print(f"[{language}] skipped: project path not found")
        return None

    run_id = f"sdk_wrapper_{language}_quickstart"
    output_path = Path(f"runs/{run_id}.jsonl")

    return RunConfig(
        id=run_id,
        mode="project",
        language=language,
        project=ProjectConfig(path=project_path),
        file=FileConfig(
            code_file=settings["code_file"],
            test_file=settings["test_file"],
        ),
        candidates=None,
        setup=SetupConfig(commands=[]),
        eval=EvalConfig(
            commands=[
                EvalCommandConfig(
                    name="tests",
                    command=settings["test_command"],
                    result_format=settings["result_format"],
                )
            ],
            stop_on_first_failure=False,
            score_strategy="weighted",
        ),
        output=OutputConfig(path=output_path),
        rank=RankConfig(enabled=True, profile="default", out=None, top=None),
        runner=RunnerConfig(workers=workers),
        sandbox=SandboxConfig(
            image=settings["image"],
            timeout=20,
            memory="512m",
            cpus="1",
            pids_limit=128,
            network=False,
        ),
        viewer=ViewerConfig(enabled=False, out=None, open=False),
        raw={},
        base_dir=Path(".").resolve(),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run coderoll quickstart examples with SDK wrapper classes only.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["python", "javascript", "typescript", "go"],
        choices=["python", "javascript", "typescript", "go"],
        help="Languages to run.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Runner workers per language run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for language in args.languages:
        config = build_run_config(language=language, workers=args.workers)
        if config is None:
            continue
        results = run_from_config(config)
        print(f"[{language}] output: {config.output_path}")
        print(f"[{language}] summary: {results.summary()}")


if __name__ == "__main__":
    main()
