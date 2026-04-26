# coderoll examples

These examples cover the current config-first evaluation flow.

Build the Python sandbox image once:

```bash
uv run python -m coderoll build-image --runtime python --tag coderoll-python:3.11
```

YAML configs require PyYAML in the calling environment:

```bash
uv run --with pyyaml python -m coderoll validate-config examples/project_python/experiment.yaml
```

Run each sample:

```bash
uv run --with pyyaml python -m coderoll run examples/project_python/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/single_candidate/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/json_array/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/directory_candidate/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/candidate_dependencies/experiment.yaml
uv run --with pyyaml python -m coderoll run examples/multi_command_eval/experiment.yaml
```

Inspect outputs:

```bash
uv run python -m coderoll rank runs/project_python_results.jsonl
uv run python -m coderoll view runs/project_python_results.jsonl --no-open
uv run python -m coderoll export runs/project_python_results.jsonl --format rewards --out datasets/project_python_rewards.jsonl
```

Sample map:

- `project_python`: JSONL multi-file candidates over a base project.
- `single_candidate`: one `candidate.json` with `code` written to `entry_file`.
- `json_array`: one JSON file containing multiple code candidates.
- `directory_candidate`: a whole candidate project directory copied over the base project.
- `candidate_dependencies`: candidate-level dependency commands enabled and run inside Docker.
- `multi_command_eval`: compile check plus tests, demonstrating partial scoring across commands.
