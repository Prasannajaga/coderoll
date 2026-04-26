# coderoll

`coderoll` is a lightweight, dependency-free, local-first Python library for code rollout collection and evaluation.

It takes a coding task and one or more candidate solutions, runs each candidate inside a local Docker sandbox, executes tests, scores outcomes, stores full traces as JSONL, and ranks candidates.

## What coderoll is

- A dependency-free local code rollout/eval library
- Focused on clean rollout data collection for future RL/SFT workflows
- Simple CLI + Python API

## CLI usage

```bash
coderoll --help
```

```bash
coderoll init TASK_DIR
coderoll init-config PATH [--force]
coderoll build-image [--runtime python|javascript|typescript] [--tag TAG]
coderoll run CONFIG.{toml,yaml,yml}
coderoll run TASK_DIR [--candidate FILE | --candidates FILE.jsonl] --out RESULTS.jsonl [--workers N]
coderoll rank RESULTS.jsonl [--top N] [--show-code] [--passed | --failed]
coderoll inspect RESULTS.jsonl --id CANDIDATE_ID
coderoll view RESULTS.jsonl [--out REPORT.html] [--title TITLE] [--no-open]
coderoll export RESULTS.jsonl --format {sft,preference,rewards} --out DATASET.jsonl [--include-metadata]
```

## Build Runtime Images

```bash
coderoll build-image --runtime python
coderoll build-image --runtime javascript
coderoll build-image --runtime typescript
```

Python package runtime dependencies stay empty. JavaScript and TypeScript tooling lives inside Docker images only.

## Config-First Runs

Preferred usage puts all runtime arguments in a YAML or TOML config:

```bash
coderoll run examples/project_mode/experiment.yaml
coderoll run examples/file_mode/experiment.yaml
# also supported:
coderoll run --config examples/file_mode/experiment.yaml
```

Config files contain a top-level mode, setup/eval commands, output path, workers, sandbox settings, and viewer settings. Relative paths resolve from the config file directory.

`coderoll` supports exactly two config modes:

- `mode: project`: evaluate one complete generated project directory.
- `mode: file`: evaluate JSON/JSONL candidates that contain generated files.

If a file-mode candidate includes both generated code and generated tests, coderoll verifies that the code passes those generated tests. This is useful as a smoke check, but it does not prove real correctness. For real evaluation, prefer trusted tests written outside the model, hidden verifier tests, or existing project test suites.

TOML configs work dependency-free through stdlib `tomllib`. YAML configs require the optional extra:

```bash
pip install "coderoll[yaml]"
```

You can generate a starter config:

```bash
coderoll init-config coderoll.toml
coderoll init-config coderoll.yaml
```

## Backward-Compatible Flag Mode

The older task-directory CLI still works:

```bash
coderoll init tmp/scratch_task
coderoll run tmp/scratch_task --candidates tmp/scratch_task/candidates.jsonl --out runs/scratch_task.jsonl
coderoll run tmp/scratch_task --candidate solution.py --out runs/scratch_task.single.jsonl
```

## Create a Python Task

```bash
coderoll init examples/scratch_task
```

## Rank results

```bash
coderoll rank runs/file_mode_results.jsonl --top 5
coderoll rank runs/file_mode_results.jsonl --top 5 --show-code
coderoll rank runs/file_mode_results.jsonl --passed
coderoll rank runs/file_mode_results.jsonl --failed
```

## Inspect one candidate

```bash
coderoll inspect runs/file_mode_results.jsonl --id good
```

## Viewing results locally

```bash
coderoll view runs/file_mode_results.jsonl
coderoll view runs/file_mode_results.jsonl --out reports/file_mode.html --no-open
```

This generates a standalone static HTML report (for example `runs/file_mode.viewer.html`).
No server is required, no runtime dependencies are added, and the report can be shared as a single file.

## Exporting datasets

`coderoll` can export collected run records into training-ready JSONL datasets.
No training is performed. These are plain data conversions only.

1. SFT:
   best passing solution per task
2. Preference:
   chosen passing solution vs rejected failing solution
3. Rewards:
   all candidates with score as reward

```bash
coderoll export runs/file_mode_results.jsonl --format sft --out datasets/sft.jsonl
coderoll export runs/file_mode_results.jsonl --format preference --out datasets/preferences.jsonl
coderoll export runs/file_mode_results.jsonl --format rewards --out datasets/rewards.jsonl
coderoll export runs/file_mode_results.jsonl --format rewards --out datasets/rewards_meta.jsonl --include-metadata
```

`stdout`/`stderr` are excluded by default.
Use `--include-metadata` to include extra fields such as hashes, duration, and timestamps.

## Python API

```python
from coderoll import (
    Task,
    Candidate,
    DockerSandbox,
    PytestEvaluator,
    JsonlStore,
    Runner,
)

task = Task.from_dir("tmp/scratch_task")

candidates = [
    Candidate(
        code=(
            "def solution(x):\n"
            "    return x + 1\n"
        ),
        id="api_good",
    ),
]

runner = Runner(
    sandbox=DockerSandbox(timeout=5),
    evaluator=PytestEvaluator(),
    store=JsonlStore("runs/scratch_task.jsonl"),
)

results = runner.run(task, candidates)
print(results.best())
print(results.top_k(3))

results2 = runner.run_strings(
    task,
    [
        "def solution(x):\n    return x + 1\n",
    ],
)
```

## Security notes

- Docker sandboxing is local isolation, not perfect isolation
- Network is disabled by default (`--network none`)
- Memory/CPU/pids limits are enabled by default
- Avoid running hostile code without stronger isolation
- Never mount sensitive directories or Docker socket
- `LocalSubprocessSandbox` is unsafe for untrusted code

## Data format (JSONL)

Each line is a complete run record:

```json
{"run_id":"run_123","task_id":"file_mode_eval","mode":"file","candidate_id":"good","score":1.0,"passed":true,"stdout":".","stderr":"","files":{"solution.py":"def add_one(x):\n    return x + 1\n"}}
```
