# coderoll examples

The config-first API has two modes:

- `project`: evaluate one complete generated project directory.
- `file`: evaluate JSON/JSONL candidates that each contain generated files.

Build the Python sandbox image once:

```bash
uv run python -m coderoll build-image --runtime python --tag coderoll-python:3.11
```

YAML configs require PyYAML in the calling environment:

```bash
uv run --with pyyaml python -m coderoll validate-config examples/project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/file_mode/experiment.yaml
```

Run the samples:

```bash
uv run --with pyyaml python -m coderoll run examples/project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/file_mode/experiment.yaml
```

Inspect outputs:

```bash
uv run python -m coderoll rank runs/file_mode_results.jsonl
uv run python -m coderoll view runs/file_mode_results.jsonl --no-open
uv run python -m coderoll export runs/file_mode_results.jsonl --format rewards --out datasets/file_rewards.jsonl
```

Generated tests note: if a file-mode candidate includes both generated code and generated tests,
coderoll verifies only that the code passes those generated tests. That is useful for smoke checks,
but it does not prove real correctness. For real evaluation, prefer trusted tests written outside
the model, hidden verifier tests, or existing project test suites.
