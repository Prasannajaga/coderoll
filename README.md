# coderoll

`coderoll` is a local-first Python tool to evaluate AI-generated code in Docker sandboxes.

It runs candidates, executes tests, and writes JSONL results you can rank, inspect, and export.

## Quick Start

```bash
coderoll --help
```

```bash
# create a starter config
coderoll init-config experiment.yaml

# run an experiment from config
coderoll run experiment.yaml

# rank outputs
coderoll rank runs/results.jsonl --top 5

# inspect one candidate
coderoll inspect runs/results.jsonl --id CANDIDATE_ID

# open HTML report
coderoll view runs/results.jsonl
```

## Core Commands

```bash
coderoll init TASK_DIR
coderoll init-config PATH [--force]
coderoll build-image [--runtime python|javascript|typescript] [--tag TAG]
coderoll run [TASK_DIR or CONFIG]
coderoll validate-config CONFIG.{toml,yaml,yml}
coderoll rank RESULTS.jsonl
coderoll inspect RESULTS.jsonl --id CANDIDATE_ID
coderoll view RESULTS.jsonl
coderoll export RESULTS.jsonl --format {sft,preference,rewards} --out DATASET.jsonl
```

## Config Modes

- `mode: project` evaluates a full generated project directory.
- `mode: file` evaluates candidates from JSON/JSONL.

## Notes

- Python, JavaScript, and TypeScript runtimes are supported.
- YAML config support requires:

```bash
pip install "coderoll[yaml]"
```
