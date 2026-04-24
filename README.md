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

## Rank results

```bash
coderoll rank runs/add_one.jsonl --top 5
```

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
