from argparse import ArgumentParser, SUPPRESS
from pathlib import Path
import subprocess
import tempfile
import webbrowser
from typing import Sequence

from .candidate import Candidate
from .config import load_config
from .errors import CandidateError, CoderollError, StoreError
from .evaluators.pytest_eval import PytestEvaluator
from .exporters import export_preferences, export_rewards, export_sft
from .rankers.simple import rank_records
from .runner import Runner, run_from_config
from .runtimes import get_runtime
from .sandboxes.docker_cli import DockerSandbox
from .stores.jsonl import JsonlStore
from .task import Task
from .viewer import default_viewer_path, write_viewer


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            _cmd_init(Path(args.task_dir))
        elif args.command == "init-config":
            _cmd_init_config(Path(args.path), force=args.force)
        elif args.command == "build-image":
            _cmd_build_image(args.tag, args.runtime, args.python_version)
        elif args.command == "run":
            _cmd_run(
                task_dir=Path(args.task_dir) if args.task_dir else None,
                candidate_file=Path(args.candidate) if args.candidate else None,
                candidates_file=Path(args.candidates) if args.candidates else None,
                out_path=Path(args.out) if args.out else None,
                workers=args.workers,
                config_path=Path(args.config) if args.config else None,
            )
        elif args.command == "validate-config":
            _cmd_validate_config(Path(args.config))
        elif args.command == "rank":
            _cmd_rank(
                results_path=Path(args.results_jsonl),
                top=args.top,
                show_code=args.show_code,
                only_failed=args.failed,
                only_passed=args.passed,
            )
        elif args.command == "inspect":
            _cmd_inspect(Path(args.results_jsonl), args.candidate_id)
        elif args.command == "view":
            _cmd_view(
                results_path=Path(args.results_jsonl),
                out_path=Path(args.out) if args.out else None,
                title=args.title,
                no_open=args.no_open,
            )
        elif args.command == "export":
            _cmd_export(
                results_path=Path(args.results_jsonl),
                format_name=args.format,
                out_path=Path(args.out),
                include_metadata=args.include_metadata,
            )
        else:
            parser.print_help()
            return 1
    except (CoderollError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    return 0


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="coderoll", description="Local code rollout and evaluation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a starter task directory")
    init_parser.add_argument("task_dir", help="Task directory to create")

    init_config_parser = subparsers.add_parser(
        "init-config",
        help="Create a sample run config file (.toml/.yaml/.yml)",
    )
    init_config_parser.add_argument("path", help="Config file path to create")
    init_config_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite config file if it already exists",
    )

    build_parser = subparsers.add_parser("build-image", help="Build a local Docker eval image")
    build_parser.add_argument("--tag", help="Docker image tag")
    build_parser.add_argument(
        "--runtime",
        default="python",
        help="Runtime image to build: python, javascript, or typescript",
    )
    build_parser.add_argument("--python-version", default="3.11", help=SUPPRESS)

    run_parser = subparsers.add_parser("run", help="Run candidates for a task")
    run_parser.add_argument("task_dir", nargs="?", help="Path to task directory")
    group = run_parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--candidate", help="Path to one candidate .py file")
    group.add_argument("--candidates", help="Path to candidates.jsonl")
    run_parser.add_argument("--out", help="Output JSONL file")
    run_parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    run_parser.add_argument("--config", help="Run configuration file (.toml/.yaml/.yml)")

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate and print a normalized run config without executing Docker",
    )
    validate_parser.add_argument("config", help="Run configuration file (.toml/.yaml/.yml)")

    rank_parser = subparsers.add_parser("rank", help="Rank candidates from a results JSONL")
    rank_parser.add_argument("results_jsonl", help="Results JSONL path")
    rank_parser.add_argument("--top", type=int, default=5, help="Number of top results")
    rank_parser.add_argument("--show-code", action="store_true", help="Print code blocks")
    rank_parser.add_argument("--failed", action="store_true", help="Show only failed records")
    rank_parser.add_argument("--passed", action="store_true", help="Show only passed records")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one candidate by id")
    inspect_parser.add_argument("results_jsonl", help="Results JSONL path")
    inspect_parser.add_argument("--id", dest="candidate_id", required=True, help="Candidate id")

    view_parser = subparsers.add_parser("view", help="Generate a local static HTML results viewer")
    view_parser.add_argument("results_jsonl", help="Results JSONL path")
    view_parser.add_argument("--out", help="Output HTML path")
    view_parser.add_argument("--title", help="Report title")
    view_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not auto-open the HTML report in a browser",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Export training-ready JSONL datasets from run records",
    )
    export_parser.add_argument("results_jsonl", help="Results JSONL path")
    export_parser.add_argument("--format", required=True, help="Export format: sft|preference|rewards")
    export_parser.add_argument("--out", required=True, help="Output JSONL path")
    export_parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include additional metadata fields in exported rows",
    )

    return parser


def _cmd_init(task_dir: Path) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)

    task_id = task_dir.name
    prompt = "Write a function solution(x) that returns x + 1.\n"
    test_code = (
        "from solution import solution\n\n"
        "def test_add_one():\n"
        "    assert solution(1) == 2\n"
        "    assert solution(10) == 11\n"
    )
    task_toml = (
        f'id = "{task_id}"\n'
        'entry_file = "solution.py"\n'
        'test_file = "test_solution.py"\n'
        'test_command = "python -m pytest -q"\n'
        "timeout = 5\n"
    )
    candidates_jsonl = (
        '{"id": "good", "code": "def solution(x): return x + 1"}\n'
        '{"id": "bad", "code": "def solution(x): return x"}\n'
    )

    _write_if_missing(task_dir / "prompt.txt", prompt)
    _write_if_missing(task_dir / "test_solution.py", test_code)
    _write_if_missing(task_dir / "task.toml", task_toml)
    _write_if_missing(task_dir / "candidates.jsonl", candidates_jsonl)

    print(f"Initialized task at {task_dir}")


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def _cmd_init_config(path: Path, force: bool = False) -> None:
    if path.exists() and not force:
        raise CoderollError(f"Config file already exists: {path}. Use --force to overwrite.")

    suffix = path.suffix.lower()
    if suffix == ".toml":
        content = _sample_toml_config()
    elif suffix in {".yaml", ".yml"}:
        content = _sample_yaml_config()
    else:
        raise CoderollError("Config path must end with .toml, .yaml, or .yml")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Initialized config at {path}")


def _sample_yaml_config() -> str:
    return (
        "id: file_mode_eval\n"
        "mode: file\n\n"
        "candidates:\n"
        "  path: examples/file_mode/candidates.jsonl\n"
        "  type: jsonl\n\n"
        "file:\n"
        "  code_file: solution.py\n"
        "  test_file: test_solution.py\n\n"
        "setup:\n"
        "  commands: []\n\n"
        "eval:\n"
        "  commands:\n"
        "    - name: tests\n"
        "      command: python -m pytest -q --junitxml=.coderoll-results.xml\n"
        "      result_format: junit\n\n"
        "output:\n"
        "  path: runs/file_mode_results.jsonl\n\n"
        "runner:\n"
        "  workers: 1\n\n"
        "sandbox:\n"
        "  image: coderoll-python:3.11\n"
        "  timeout: 10\n"
        "  memory: 512m\n"
        "  cpus: \"1\"\n"
        "  pids_limit: 128\n"
        "  network: false\n\n"
        "viewer:\n"
        "  enabled: true\n"
        "  out: runs/file_mode.viewer.html\n"
        "  open: false\n"
    )


def _sample_toml_config() -> str:
    return (
        'id = "file_mode_eval"\n'
        'mode = "file"\n\n'
        "[candidates]\n"
        'path = "examples/file_mode/candidates.jsonl"\n'
        'type = "jsonl"\n\n'
        "[file]\n"
        'code_file = "solution.py"\n'
        'test_file = "test_solution.py"\n\n'
        "[setup]\n"
        "commands = []\n\n"
        "[[eval.commands]]\n"
        'name = "tests"\n'
        'command = "python -m pytest -q --junitxml=.coderoll-results.xml"\n'
        'result_format = "junit"\n\n'
        "[output]\n"
        'path = "runs/file_mode_results.jsonl"\n\n'
        "[runner]\n"
        "workers = 1\n\n"
        "[sandbox]\n"
        'image = "coderoll-python:3.11"\n'
        "timeout = 10\n"
        'memory = "512m"\n'
        'cpus = "1"\n'
        "pids_limit = 128\n"
        "network = false\n\n"
        "[viewer]\n"
        "enabled = true\n"
        'out = "runs/file_mode.viewer.html"\n'
        "open = false\n"
    )


def _cmd_build_image(tag: str | None, runtime: str, python_version: str = "3.11") -> None:
    spec = get_runtime(runtime)
    image_tag = tag or spec.default_image
    dockerfile_content = _dockerfile_for_runtime(spec.language, python_version)

    with tempfile.TemporaryDirectory(prefix="coderoll_build_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        dockerfile_path = tmp_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

        command = ["docker", "build", "-t", image_tag, str(tmp_dir)]
        print(f"Building Docker image {image_tag} for runtime {spec.language}...")

        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise CoderollError(
                "Docker CLI was not found. Install Docker and ensure `docker` is on PATH."
            ) from exc

        if completed.returncode != 0:
            print(completed.stdout)
            print(completed.stderr)
            raise CoderollError("Docker image build failed")

        print(f"Successfully built image: {image_tag}")


def _dockerfile_for_runtime(runtime: str, python_version: str = "3.11") -> str:
    if runtime == "python":
        return (
            f"FROM python:{python_version}-slim\n"
            "RUN pip install --no-cache-dir pytest\n"
            "WORKDIR /workspace\n"
        )
    if runtime == "javascript":
        return "FROM node:20-slim\nWORKDIR /workspace\n"
    if runtime == "typescript":
        return (
            "FROM node:20-slim\n"
            "RUN npm install -g typescript tsx\n"
            "WORKDIR /workspace\n"
        )
    raise CoderollError(f"Unsupported runtime: {runtime}")


def _cmd_run(
    task_dir: Path | None,
    candidate_file: Path | None,
    candidates_file: Path | None,
    out_path: Path | None,
    workers: int,
    config_path: Path | None,
) -> None:
    if config_path is not None:
        if task_dir is not None and _is_config_path(task_dir):
            raise ValueError("Use either --config or positional config file, not both.")
        if task_dir is not None:
            raise ValueError("Use either --config or positional TASK_DIR, not both.")
        if candidate_file is not None or candidates_file is not None or out_path is not None:
            raise ValueError(
                "When using --config, do not pass --candidate, --candidates, or --out."
            )
        _cmd_run_from_config(config_path)
        return

    if task_dir is None:
        raise ValueError("TASK_DIR is required when --config is not used.")
    if _is_config_path(task_dir):
        if candidate_file is not None or candidates_file is not None or out_path is not None:
            raise ValueError(
                "When using config mode, do not pass --candidate, --candidates, or --out."
            )
        _cmd_run_from_config(task_dir)
        return
    if not task_dir.is_dir():
        raise ValueError(f"Run path must be a config file or task directory: {task_dir}")
    if out_path is None:
        raise ValueError("--out is required when --config is not used.")

    task = Task.from_dir(task_dir)

    if candidate_file is not None:
        candidates = [Candidate.from_file(candidate_file)]
    elif candidates_file is not None:
        candidates = Candidate.from_jsonl(candidates_file)
    else:
        raise CandidateError("Either --candidate or --candidates must be provided")

    if not candidates:
        raise CandidateError("No candidates were loaded")

    runner = Runner(
        sandbox=DockerSandbox(timeout=task.timeout),
        evaluator=PytestEvaluator(),
        store=JsonlStore(out_path),
    )

    results = runner.run(task, candidates, workers=workers)
    _print_run_summary(
        task_id=task.id,
        output_path=out_path,
        summary=results.summary(),
        errors=[record.error for record in results.records if record.error],
    )


def _cmd_run_from_config(config_path: Path) -> None:
    cfg = load_config(config_path)
    results = run_from_config(cfg)
    _print_run_summary(
        task_id=cfg.id,
        output_path=cfg.output_path,
        summary=results.summary(),
        errors=[record.error for record in results.records if record.error],
        config_id=cfg.id,
    )

    if cfg.viewer.enabled:
        viewer_out = Path(cfg.viewer.out) if cfg.viewer.out else default_viewer_path(cfg.output_path)
        title = f"coderoll run: {cfg.id}"
        written = write_viewer(results.records, viewer_out, title=title)
        print(f"viewer: {written}")
        if cfg.viewer.open:
            webbrowser.open(written.resolve().as_uri())


def _is_config_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".toml", ".yaml", ".yml"}


def _cmd_rank(
    results_path: Path,
    top: int,
    show_code: bool,
    only_failed: bool,
    only_passed: bool,
) -> None:
    if only_failed and only_passed:
        raise ValueError("Use only one of --failed or --passed")

    records = JsonlStore(results_path).read_all()
    if only_failed:
        records = [record for record in records if not record.passed]
    if only_passed:
        records = [record for record in records if record.passed]

    ranked = rank_records(records)
    if top > 0:
        ranked = ranked[:top]

    if not ranked:
        print("No matching records found")
        return

    for record in ranked:
        print(
            f"candidate_id={record.candidate_id} "
            f"score={record.score:.3f} "
            f"passed={record.passed} "
            f"duration_ms={record.duration_ms}"
        )
        if show_code:
            if record.files:
                print("--- files ---")
                for path, content in sorted(record.files.items()):
                    print(f"### {path}")
                    print(content)
            else:
                print("--- code ---")
                print(record.code)
            print("------------")


def _cmd_inspect(results_path: Path, candidate_id: str) -> None:
    match = None
    for record in JsonlStore(results_path).iter_records():
        if record.candidate_id == candidate_id:
            match = record
            break

    if match is None:
        raise StoreError(f"Candidate id not found: {candidate_id}")

    print(f"task_id: {match.task_id}")
    print(f"candidate_id: {match.candidate_id}")
    print(f"score: {match.score}")
    print(f"passed: {match.passed}")
    print(f"exit_code: {match.exit_code}")
    print(f"duration_ms: {match.duration_ms}")
    print("stdout:")
    print(match.stdout)
    print("stderr:")
    print(match.stderr)
    print("code:")
    print(match.code)
    if match.files:
        print("files:")
        for path, content in sorted(match.files.items()):
            print(f"--- {path} ---")
            print(content)


def _cmd_validate_config(config_path: Path) -> None:
    cfg = load_config(config_path)
    from dataclasses import asdict
    import json

    data = asdict(cfg)
    data["base_dir"] = str(cfg.base_dir)
    data["output_path"] = str(cfg.output_path)
    if cfg.project is not None:
        data["project"]["path"] = str(cfg.project.path)
    if cfg.candidates is not None:
        data["candidates"]["path"] = str(cfg.candidates.path)
        data["candidates_path"] = str(cfg.candidates.path)
    print(json.dumps(data, indent=2, default=str))


def _print_run_summary(
    task_id: str,
    output_path: Path,
    summary: dict[str, object],
    errors: list[str | None],
    config_id: str | None = None,
) -> None:
    if config_id is not None:
        print(f"config_id: {config_id}")
    print(f"task_id: {task_id}")
    print(f"total: {summary['total']}")
    print(f"passed: {summary['passed']}")
    print(f"failed: {summary['failed']}")
    print(f"best_score: {summary['best_score']}")
    print(f"output: {output_path}")
    first_error = next((error for error in errors if error), None)
    if first_error is not None:
        print(f"first_error: {first_error}")


def _cmd_view(
    results_path: Path,
    out_path: Path | None,
    title: str | None,
    no_open: bool,
) -> None:
    records = JsonlStore(results_path).read_all()
    target = out_path or default_viewer_path(results_path)
    written = write_viewer(records, target, title=title)
    print(f"viewer: {written}")

    if not no_open:
        webbrowser.open(written.resolve().as_uri())


def _cmd_export(
    results_path: Path,
    format_name: str,
    out_path: Path,
    include_metadata: bool,
) -> None:
    records = JsonlStore(results_path).read_all()
    format_key = format_name.strip().lower()
    if format_key == "sft":
        rows = export_sft(records, out_path, include_metadata=include_metadata)
    elif format_key == "preference":
        rows = export_preferences(records, out_path, include_metadata=include_metadata)
    elif format_key == "rewards":
        rows = export_rewards(records, out_path, include_metadata=include_metadata)
    else:
        raise ValueError("Invalid format. Supported formats are: sft, preference, rewards")

    print(f"format: {format_key}")
    print(f"input: {results_path}")
    print(f"output: {out_path}")
    print(f"rows_exported: {rows}")
