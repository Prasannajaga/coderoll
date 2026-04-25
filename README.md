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
coderoll run examples/python_add_one.yaml
coderoll run examples/js_add_one.yaml
coderoll run examples/ts_add_one.yaml
# also supported:
coderoll run --config examples/python_add_one.yaml
```

Config files contain task path, candidates path, output path, workers, sandbox settings, and viewer settings. Relative paths resolve from the config file directory.

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
coderoll run examples/add_one --candidates examples/add_one/candidates.jsonl --out runs/add_one.jsonl
coderoll run examples/add_one --candidate solution.py --out runs/add_one.single.jsonl
```

## Create a Python Task

```bash
coderoll init examples/add_one
```

## Rank results

```bash
coderoll rank runs/add_one.jsonl --top 5
coderoll rank runs/add_one.jsonl --top 5 --show-code
coderoll rank runs/add_one.jsonl --passed
coderoll rank runs/add_one.jsonl --failed
```

## Inspect one candidate

```bash
coderoll inspect runs/add_one.jsonl --id good
```

## Viewing results locally

```bash
coderoll view runs/add_one.jsonl
coderoll view runs/add_one.jsonl --out reports/add_one.html --no-open
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
coderoll export runs/add_one.jsonl --format rewards --out datasets/rewards_meta.jsonl --include-metadata
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
