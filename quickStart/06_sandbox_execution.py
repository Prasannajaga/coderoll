from __future__ import annotations

import json
from pathlib import Path

from coderoll.config import (
    CandidatesConfig,
    EvalCommandConfig,
    EvalConfig,
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


def write_single_candidate(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": "hello_stdout",
        "code": "print('hello from coderoll sandbox')",
        "metadata": {"source": "quickstart_inline"},
    }
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def build_config(candidates_path: Path, output_path: Path) -> RunConfig:
    return RunConfig(
        id="sdk_sandbox_stdout",
        mode="file",
        language="python",
        project=None,
        file=FileConfig(code_file="solution.py", test_file="test_solution.py"),
        candidates=CandidatesConfig(path=candidates_path, type="jsonl"),
        setup=SetupConfig(commands=[]),
        eval=EvalConfig(
            commands=[
                EvalCommandConfig(
                    name="run_code",
                    command="python solution.py",
                    result_format="exit_code",
                )
            ],
            stop_on_first_failure=True,
            score_strategy="weighted",
        ),
        output=OutputConfig(path=output_path),
        rank=RankConfig(enabled=False, profile="default", out=None, top=None),
        runner=RunnerConfig(workers=1),
        sandbox=SandboxConfig(
            image="coderoll-python:3.11",
            timeout=10,
            memory="256m",
            cpus="1",
            pids_limit=128,
            network=False,
        ),
        viewer=ViewerConfig(enabled=False, out=None, open=False),
        raw={},
        base_dir=Path(".").resolve(),
    )


def main() -> None:
    candidates_path = Path("runs/quickstart_inline_candidates.jsonl")
    output_path = Path("runs/sdk_sandbox_stdout.jsonl")

    write_single_candidate(candidates_path)
    config = build_config(candidates_path=candidates_path, output_path=output_path)

    results = run_from_config(config)
    first = results.records[0] if results.records else None

    print("summary:", results.summary())
    if first is not None:
        print("candidate_id:", first.candidate_id)
        print("passed:", first.passed)
        print("score:", first.score)
        print("stdout:", first.stdout.strip())
        print("exit_code:", first.exit_code)
    print("jsonResult:", output_path)


if __name__ == "__main__":
    main()
