# coderoll SDK quick start

These examples show the Python SDK path for the same flows you can run from the CLI.

Run from the repository root.

## 1. Run an experiment config

```bash
uv run --with pyyaml python quickStart/01_run_config.py
```

This loads `examples/file_mode/experiment.yaml`, runs it, writes JSONL records, and prints a short summary.

## 2. Rank saved results

```bash
uv run python quickStart/02_rank_results.py
```

This reads `runs/file_mode_results.jsonl` and prints candidates ordered by score.

## 3. Generate viewer and exports

```bash
uv run python quickStart/03_view_and_export.py
```

This writes:

- `runs/file_mode.sdk.viewer.html`
- `datasets/file_mode_rewards.sdk.jsonl`
- `datasets/file_mode_sft.sdk.jsonl`
- `datasets/file_mode_preferences.sdk.jsonl`

## 4. Build a config object in Python

```bash
uv run python quickStart/04_build_config_in_python.py
```

This creates a `RunConfig` directly instead of loading YAML.

## 5. Run one inline code snippet in Docker sandbox

```bash
uv run python quickStart/06_sandbox_execution.py
```

This creates one JSONL candidate in-memory style, runs `python solution.py` inside Docker, and prints:

- sandbox `stdout`
- pass/fail + score
- `jsonResult` path (`runs/sdk_sandbox_stdout.jsonl`)

## Docker image

The Python sample expects this image:

```bash
uv run python -m coderoll build-image --runtime python --tag coderoll-python:3.11
```

## Main SDK imports

```python
from coderoll.config import load_config
from coderoll.runner import run_from_config
from coderoll.stores.jsonl import JsonlStore
from coderoll.rankers.simple import rank_records
from coderoll.viewer import write_viewer
from coderoll.exporters import export_rewards, export_sft, export_preferences
```

Use `load_config(...) + run_from_config(...)` for the current two-mode architecture.
