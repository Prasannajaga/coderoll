# Example Suite

Project-mode examples by language and complexity:

- `example/python/project/simple/experiment.yaml`
- `example/python/project/complex/experiment.yaml`
- `example/python/project/nested/experiment.yaml`
- `example/js/project/simple/experiment.yaml`
- `example/js/project/complex/experiment.yaml`
- `example/js/project/nested/experiment.yaml`
- `example/ts/project/simple/experiment.yaml`
- `example/ts/project/complex/experiment.yaml`
- `example/ts/project/nested/experiment.yaml`

Run any example from the repo root:

```bash
uv run python -m coderoll validate-config <path-to-experiment.yaml>
uv run python -m coderoll run <path-to-experiment.yaml>
```

## 100-case evaluation packs (70% pass / 30% fail)

Each project folder also contains:

- `candidates_100.jsonl` (100 candidates: 70 expected pass, 30 expected fail)
- `experiment_100.yaml` (file-mode config that evaluates those candidates)

Example:

```bash
uv run --with pyyaml python -m coderoll validate-config example/js/project/complex/experiment_100.yaml
uv run --with pyyaml python -m coderoll run example/js/project/complex/experiment_100.yaml
```

To regenerate all 100-case packs:

```bash
python3 example/generate_eval_sets.py
```
