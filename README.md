# coderoll

`coderoll` is a lightweight, dependency-free, local-first Python library for code rollout collection and evaluation.

It takes a coding task and one or more candidate solutions, runs each candidate inside a local Docker sandbox, executes pytest, scores outcomes, stores full traces as JSONL, and ranks candidates.

## What coderoll is

- A dependency-free local code rollout/eval library
- Focused on clean rollout data collection for future RL/SFT workflows
- Simple CLI + Python API

## What coderoll is not

- Not an RL trainer
- Not an agent framework
- Not an LLM provider wrapper
- Not a web app or database service

## Install from source

```bash
pip install -e .
```

## Build Docker image

```bash
coderoll build-image
```

## Create a task

```bash
coderoll init examples/add_one
```

## Run candidates

```bash
coderoll run examples/add_one --candidates examples/add_one/candidates.jsonl --out runs/add_one.jsonl
```

## Config-driven runs

```bash
coderoll init-config coderoll.yaml
coderoll run --config coderoll.yaml
```

- TOML run config works dependency-free via stdlib `tomllib`
- YAML run config requires optional extra:
  - `pip install "coderoll[yaml]"`
- `task.toml` remains task-level config
- `coderoll.toml` / `coderoll.yaml` is run-level experiment config

## Rank results

```bash
coderoll rank runs/add_one.jsonl --top 5
```

## Viewing results locally

```bash
coderoll view runs/add_one.jsonl
```

This generates a standalone static HTML report (for example `runs/add_one.viewer.html`).
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
coderoll export runs/add_one.jsonl --format sft --out datasets/sft.jsonl
coderoll export runs/add_one.jsonl --format preference --out datasets/preferences.jsonl
coderoll export runs/add_one.jsonl --format rewards --out datasets/rewards.jsonl
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

task = Task.from_dir("examples/add_one")

candidates = [
    Candidate(code="def solution(x): return x + 1", id="good"),
    Candidate(code="def solution(x): return x", id="bad"),
]

runner = Runner(
    sandbox=DockerSandbox(timeout=5),
    evaluator=PytestEvaluator(),
    store=JsonlStore("runs/add_one.jsonl"),
)

results = runner.run(task, candidates)
print(results.best())
print(results.top_k(3))

results2 = runner.run_strings(
    task,
    [
        "def solution(x): return x + 1",
        "def solution(x): return x",
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
{"run_id":"run_123","task_id":"add_one","candidate_id":"good","score":1.0,"passed":true,"stdout":".","stderr":"","code":"def solution(x): return x + 1"}
```
