from argparse import ArgumentParser
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence

from .candidate import Candidate
from .errors import CandidateError, CoderollError, StoreError
from .evaluators.pytest_eval import PytestEvaluator
from .rankers.simple import rank_records
from .runner import Runner
from .sandboxes.docker_cli import DockerSandbox
from .stores.jsonl import JsonlStore
from .task import Task


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            _cmd_init(Path(args.task_dir))
        elif args.command == "build-image":
            _cmd_build_image(args.tag, args.python_version)
        elif args.command == "run":
            _cmd_run(
                task_dir=Path(args.task_dir),
                candidate_file=Path(args.candidate) if args.candidate else None,
                candidates_file=Path(args.candidates) if args.candidates else None,
                out_path=Path(args.out),
                workers=args.workers,
            )
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

    build_parser = subparsers.add_parser("build-image", help="Build the local Docker eval image")
    build_parser.add_argument("--tag", default="coderoll-python:3.11", help="Docker image tag")
    build_parser.add_argument(
        "--python-version",
        default="3.11",
        help="Python version for base image, e.g. 3.11",
    )

    run_parser = subparsers.add_parser("run", help="Run candidates for a task")
    run_parser.add_argument("task_dir", help="Path to task directory")
    group = run_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidate", help="Path to one candidate .py file")
    group.add_argument("--candidates", help="Path to candidates.jsonl")
    run_parser.add_argument("--out", required=True, help="Output JSONL file")
    run_parser.add_argument("--workers", type=int, default=1, help="Parallel workers")

    rank_parser = subparsers.add_parser("rank", help="Rank candidates from a results JSONL")
    rank_parser.add_argument("results_jsonl", help="Results JSONL path")
    rank_parser.add_argument("--top", type=int, default=5, help="Number of top results")
    rank_parser.add_argument("--show-code", action="store_true", help="Print code blocks")
    rank_parser.add_argument("--failed", action="store_true", help="Show only failed records")
    rank_parser.add_argument("--passed", action="store_true", help="Show only passed records")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one candidate by id")
    inspect_parser.add_argument("results_jsonl", help="Results JSONL path")
    inspect_parser.add_argument("--id", dest="candidate_id", required=True, help="Candidate id")

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


def _cmd_build_image(tag: str, python_version: str) -> None:
    template_path = Path(__file__).resolve().parent / "templates" / "Dockerfile"
    if not template_path.exists():
        raise CoderollError(f"Missing Dockerfile template: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    dockerfile_content = template.replace("{{python_version}}", python_version)

    with tempfile.TemporaryDirectory(prefix="coderoll_build_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        dockerfile_path = tmp_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

        command = ["docker", "build", "-t", tag, str(tmp_dir)]
        print(f"Building Docker image {tag} using Python {python_version}...")

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

        print(f"Successfully built image: {tag}")


def _cmd_run(
    task_dir: Path,
    candidate_file: Path | None,
    candidates_file: Path | None,
    out_path: Path,
    workers: int,
) -> None:
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
    summary = results.summary()

    print(f"task_id: {task.id}")
    print(f"total: {summary['total']}")
    print(f"passed: {summary['passed']}")
    print(f"failed: {summary['failed']}")
    print(f"best_score: {summary['best_score']}")
    print(f"output: {out_path}")
    errors = [record.error for record in results.records if record.error]
    if errors:
        print(f"first_error: {errors[0]}")


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
            print("--- code ---")
            print(record.code)
            print("------------")


def _cmd_inspect(results_path: Path, candidate_id: str) -> None:
    records = JsonlStore(results_path).read_all()
    match = None
    for record in records:
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
