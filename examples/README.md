# coderoll examples

The config-first API has two modes:

- `project`: evaluate one complete generated project directory.
- `file`: evaluate JSON/JSONL candidates that each contain generated files.

Set `language: python`, `language: javascript`, or `language: typescript` to use preset Docker images, file names, and default eval commands. Explicit config fields still override the preset.

Included samples:

- `project_mode`: Python project-mode evaluation.
- `file_mode`: Python file-mode evaluation.
- `js_file_mode`: JavaScript file-mode candidates using Node's built-in test runner.
- `ts_project_mode`: TypeScript project-mode evaluation with typecheck plus TAP tests.
- `complex_project_mode`: richer Python project with nested domain/rules/services layers plus broader tests.
- `complex_file_mode`: richer Python file-mode candidate pool with pass/partial/timeout/syntax variants.
- `complex_js_file_mode`: richer JavaScript file-mode candidate pool with pass/partial/timeout/syntax variants.
- `complex_ts_project_mode`: richer TypeScript project with nested pricing/rules/checkout modules.

Build the sandbox images once:

```bash
uv run python -m coderoll build-image --runtime python --tag coderoll-python:3.11
uv run python -m coderoll build-image --runtime javascript --tag coderoll-node:20
uv run python -m coderoll build-image --runtime typescript --tag coderoll-node-ts:20
```

YAML configs require PyYAML in the calling environment:

```bash
uv run --with pyyaml python -m coderoll validate-config examples/project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/js_file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/ts_project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/complex_project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/complex_file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/complex_js_file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll validate-config examples/complex_ts_project_mode/experiment.yaml
```

Run the samples:

```bash
uv run --with pyyaml python -m coderoll run examples/project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/js_file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/ts_project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/complex_project_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/complex_file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/complex_js_file_mode/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/complex_ts_project_mode/experiment.yaml
```

Inspect outputs:

```bash
uv run python -m coderoll rank runs/file_mode_results.jsonl
uv run python -m coderoll rank runs/complex_file_mode_results.jsonl --profile default --show-reason
uv run python -m coderoll rank runs/complex_file_mode_results.jsonl --profile strict --top 10 --show-reason
uv run python -m coderoll rank runs/complex_file_mode_results.jsonl --profile debug --show-reason
uv run python -m coderoll rank runs/complex_js_file_mode_results.jsonl --profile debug --show-reason
uv run python -m coderoll view runs/file_mode_results.jsonl --no-open
uv run python -m coderoll export runs/file_mode_results.jsonl --format rewards --out datasets/file_rewards.jsonl
```

Generated tests note: if a file-mode candidate includes both generated code and generated tests,
coderoll verifies only that the code passes those generated tests. That is useful for smoke checks,
but it does not prove real correctness. For real evaluation, prefer trusted tests written outside
the model, hidden verifier tests, or existing project test suites.
