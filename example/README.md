# Example Suite

All examples are now project-mode (no `candidates.jsonl` required).

Each use case has two runnable project examples:

- `experiment.yaml` -> uses `generated_project`
- `experiment_100.yaml` / `experiment_100.toml` -> uses `generated_project_v2`

Use cases by language:

- Python: `simple`, `complex`, `nested`
- JavaScript: `simple`, `complex`, `nested`
- TypeScript: `simple`, `complex`, `nested`

Run any example from repo root:

```bash
uv run python -m coderoll validate-config <path-to-experiment.yaml>
uv run python -m coderoll run <path-to-experiment.yaml>
```

Examples:

```bash
uv run --with pyyaml python -m coderoll run example/python/project/simple/experiment.yaml
uv run --with pyyaml python -m coderoll run example/python/project/simple/experiment_100.yaml

uv run --with pyyaml python -m coderoll run example/js/project/complex/experiment.yaml
uv run --with pyyaml python -m coderoll run example/js/project/complex/experiment_100.yaml

uv run --with pyyaml python -m coderoll run example/ts/project/nested/experiment.yaml
uv run --with pyyaml python -m coderoll run example/ts/project/nested/experiment_100.yaml
```

Note:
- Existing `candidates_100.jsonl` files are kept only as legacy sample data.
