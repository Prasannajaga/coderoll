# coderoll

`coderoll` is a local-first Python tool to evaluate AI-generated code in Docker sandboxes.
It runs candidates, executes tests, and writes JSONL results for ranking, inspection, and export.

## Quickstart

```bash
# 1) Optional: enable YAML configs
pip install "coderoll[yaml]"

# 2) Create a starter config
coderoll init-config experiment.yaml

# 3) Run the experiment
coderoll run experiment.yaml

# 4) View top results
coderoll rank runs/results.jsonl --top 5
```

## Basic Quickstart Examples

```bash
# inspect one candidate
coderoll inspect runs/results.jsonl --id CANDIDATE_ID

# open the HTML report in browser
coderoll view runs/results.jsonl

# export training datasets
coderoll export runs/results.jsonl --format sft --out datasets/sft.jsonl
```

```bash
# quick project-mode flow (scaffold, run, report)
coderoll init my-task
coderoll run my-task --candidates my-task/candidates.jsonl --out runs/my-task_results.jsonl
coderoll view runs/my-task_results.jsonl
```

More SDK-style examples are available in `quickStart/README.md`.

## CLI Usage

Setup

```bash
coderoll --help
coderoll init TASK_DIR
coderoll init-config PATH [--force]
coderoll build-image [--runtime go|java|javascript|python|rust|typescript] [--tag TAG]
coderoll validate-config CONFIG.{toml,yaml,yml}
```

Run

```bash
coderoll run [TASK_DIR or CONFIG]
```

Analyze

```bash
coderoll rank RESULTS.jsonl [--top N]
coderoll inspect RESULTS.jsonl --id CANDIDATE_ID
coderoll view RESULTS.jsonl
```

Export

```bash
coderoll export RESULTS.jsonl --format {sft,preference,rewards} --out DATASET.jsonl
```

## Supported Languages

- Python
- Go
- Java
- JavaScript
- Rust
- TypeScript
