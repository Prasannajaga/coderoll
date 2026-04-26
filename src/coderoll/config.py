from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import tomllib

from .errors import CoderollError
from .runtimes import get_runtime


DEFAULT_EXCLUDE = [
    ".git/**",
    "__pycache__/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".venv/**",
    "venv/**",
    "node_modules/**",
    ".coderoll/**",
]


def default_excludes() -> list[str]:
    return list(DEFAULT_EXCLUDE)


@dataclass
class ProjectConfig:
    path: Path
    id: str | None = None
    include: list[str] = field(default_factory=lambda: ["**/*"])
    exclude: list[str] = field(default_factory=default_excludes)


@dataclass
class FileConfig:
    code_file: str = "solution.py"
    test_file: str = "test_solution.py"


@dataclass
class CandidatesConfig:
    path: Path
    type: str = "jsonl"


@dataclass
class SetupConfig:
    commands: list[str] = field(default_factory=list)


@dataclass
class EvalCommandConfig:
    name: str | None = None
    command: str = ""
    result_format: str = "exit_code"


@dataclass
class EvalConfig:
    commands: list[EvalCommandConfig]
    stop_on_first_failure: bool = False
    score_strategy: str = "weighted"


@dataclass
class OutputConfig:
    path: Path


@dataclass
class SandboxConfig:
    image: str | None = None
    timeout: int = 5
    memory: str = "256m"
    cpus: str = "1"
    pids_limit: int = 128
    network: bool = False


@dataclass
class RunnerConfig:
    workers: int = 1


@dataclass
class ViewerConfig:
    enabled: bool = False
    out: str | None = None
    open: bool = True


@dataclass
class RunConfig:
    id: str
    mode: str
    language: str | None
    project: ProjectConfig | None
    file: FileConfig
    candidates: CandidatesConfig | None
    setup: SetupConfig
    eval: EvalConfig
    output: OutputConfig
    runner: RunnerConfig
    sandbox: SandboxConfig
    viewer: ViewerConfig
    raw: dict[str, Any]
    base_dir: Path

    @property
    def output_path(self) -> Path:
        return self.output.path

    @property
    def candidates_path(self) -> Path | None:
        return self.candidates.path if self.candidates is not None else None

    @property
    def task_path(self) -> None:
        return None


def load_config(path: str | Path) -> RunConfig:
    config_path = Path(path)
    data = load_config_dict(config_path)
    return normalize_config(data, config_path.resolve().parent)


def load_config_dict(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise CoderollError(f"Config file does not exist: {config_path}")

    suffix = config_path.suffix.lower()
    if suffix == ".toml":
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise CoderollError(
                "YAML config requires PyYAML. Install with: pip install 'coderoll[yaml]'"
            ) from exc
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if data is None:
            data = {}
    else:
        raise CoderollError(
            f"Unsupported config file extension: {config_path.suffix}. Use .toml, .yaml, or .yml"
        )

    if not isinstance(data, dict):
        raise CoderollError(f"Config root must be a table/object in {config_path}")

    return data


def normalize_config(data: dict[str, Any], base_dir: Path) -> RunConfig:
    run_id = _require_str(data, "id")
    mode = _require_str(data, "mode").strip().lower()
    if mode not in {"project", "file"}:
        raise CoderollError("mode must be one of: project, file")
    language = _optional_top_level_str(data, "language")
    runtime = get_runtime(language) if language is not None else None

    project = _normalize_project(data, base_dir) if mode == "project" else None
    candidates = _normalize_candidates(data, base_dir) if mode == "file" else None
    file_config = _normalize_file(data, runtime)
    setup = _normalize_setup(data)
    eval_config = _normalize_eval(data, runtime)
    output = OutputConfig(path=_resolve_required_path(data, "output", base_dir))
    runner = _normalize_runner(data)
    sandbox = _normalize_sandbox(data, runtime)
    viewer = _normalize_viewer(data, base_dir)

    if mode == "project":
        if project is None:
            raise CoderollError("project section is required when mode=project")
        if not project.path.exists():
            raise CoderollError(f"project.path does not exist: {project.path}")
        if not project.path.is_dir():
            raise CoderollError(f"project.path must be a directory: {project.path}")
    if mode == "file":
        if candidates is None:
            raise CoderollError("candidates section is required when mode=file")
        if not candidates.path.exists():
            raise CoderollError(f"candidates.path does not exist: {candidates.path}")
        if not candidates.path.is_file():
            raise CoderollError(f"candidates.path must be a file: {candidates.path}")

    return RunConfig(
        id=run_id,
        mode=mode,
        language=language,
        project=project,
        file=file_config,
        candidates=candidates,
        setup=setup,
        eval=eval_config,
        output=output,
        runner=runner,
        sandbox=sandbox,
        viewer=viewer,
        raw=dict(data),
        base_dir=base_dir,
    )


def _normalize_project(data: dict[str, Any], base_dir: Path) -> ProjectConfig:
    section = _required_section(data, "project")
    path_value = section.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise CoderollError("project.path is required and must be a non-empty string")
    return ProjectConfig(
        path=_resolve_path(Path(path_value), base_dir),
        id=_optional_str_or_none(section, "id"),
        include=_optional_str_list(section, "include", ["**/*"], "project.include"),
        exclude=_optional_str_list(section, "exclude", default_excludes(), "project.exclude"),
    )


def _normalize_file(data: dict[str, Any], runtime: Any | None = None) -> FileConfig:
    section = _optional_section(data, "file")
    default_code_file = runtime.default_entry_file if runtime is not None else "solution.py"
    default_test_file = runtime.default_test_file if runtime is not None else "test_solution.py"
    return FileConfig(
        code_file=_optional_str(section, "code_file", default_code_file),
        test_file=_optional_str(section, "test_file", default_test_file),
    )


def _normalize_candidates(data: dict[str, Any], base_dir: Path) -> CandidatesConfig:
    section = _required_section(data, "candidates")
    path_value = section.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise CoderollError("candidates.path is required and must be a non-empty string")
    type_value = str(section.get("type", "jsonl")).strip().lower()
    if type_value not in {"json", "jsonl"}:
        raise CoderollError("candidates.type must be one of: json, jsonl")
    return CandidatesConfig(
        path=_resolve_path(Path(path_value), base_dir),
        type=type_value,
    )


def _normalize_setup(data: dict[str, Any]) -> SetupConfig:
    section = _optional_section(data, "setup")
    return SetupConfig(commands=_optional_str_list(section, "commands", [], "setup.commands"))


def _normalize_eval(data: dict[str, Any], runtime: Any | None = None) -> EvalConfig:
    section = _optional_section(data, "eval")
    raw_commands = section.get("commands")
    if raw_commands is None:
        if runtime is None:
            raise CoderollError("eval.commands is required")
        raw_commands = _runtime_eval_commands(runtime)
    if not isinstance(raw_commands, list) or not raw_commands:
        raise CoderollError("eval.commands must be a non-empty list")

    default_format = str(section.get("result_format", "exit_code")).strip().lower()
    if default_format not in {"junit", "tap", "exit_code"}:
        raise CoderollError("eval.result_format must be one of: junit, tap, exit_code")

    commands: list[EvalCommandConfig] = []
    for index, item in enumerate(raw_commands):
        if isinstance(item, str):
            if not item.strip():
                raise CoderollError(f"eval.commands[{index}] must not be empty")
            commands.append(EvalCommandConfig(name=None, command=item, result_format=default_format))
        elif isinstance(item, dict):
            command = item.get("command")
            if not isinstance(command, str) or not command.strip():
                raise CoderollError(f"eval.commands[{index}].command must be a non-empty string")
            result_format = str(item.get("result_format", default_format)).strip().lower()
            if result_format not in {"junit", "tap", "exit_code"}:
                raise CoderollError(
                    f"eval.commands[{index}].result_format must be one of: junit, tap, exit_code"
                )
            name = item.get("name")
            commands.append(
                EvalCommandConfig(
                    command=command,
                    name=str(name) if name is not None else None,
                    result_format=result_format,
                )
            )
        else:
            raise CoderollError(f"eval.commands[{index}] must be a string or object")

    strategy = str(section.get("score_strategy", "weighted")).strip().lower()
    if strategy not in {"weighted", "command_average", "tests_only"}:
        raise CoderollError("eval.score_strategy must be one of: weighted, command_average, tests_only")

    return EvalConfig(
        commands=commands,
        stop_on_first_failure=_optional_bool(
            section,
            "stop_on_first_failure",
            False,
            "eval.stop_on_first_failure",
        ),
        score_strategy=strategy,
    )


def _normalize_runner(data: dict[str, Any]) -> RunnerConfig:
    section = _optional_section(data, "runner")
    workers = section.get("workers", 1)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise CoderollError("runner.workers must be an integer >= 1")
    return RunnerConfig(workers=workers)


def _normalize_sandbox(data: dict[str, Any], runtime: Any | None = None) -> SandboxConfig:
    section = _optional_section(data, "sandbox")
    default_image = runtime.default_image if runtime is not None else None
    return SandboxConfig(
        image=_optional_str_or_none(section, "image") or default_image,
        timeout=_optional_positive_int(section, "timeout", 5, "sandbox.timeout"),
        memory=_optional_str(section, "memory", "256m"),
        cpus=_optional_str(section, "cpus", "1"),
        pids_limit=_optional_positive_int(section, "pids_limit", 128, "sandbox.pids_limit"),
        network=_optional_bool(section, "network", False, "sandbox.network"),
    )


def _normalize_viewer(data: dict[str, Any], base_dir: Path) -> ViewerConfig:
    section = _optional_section(data, "viewer")
    viewer = ViewerConfig(
        enabled=_optional_bool(section, "enabled", False, "viewer.enabled"),
        out=_optional_str_or_none(section, "out"),
        open=_optional_bool(section, "open", True, "viewer.open"),
    )
    if viewer.out is not None:
        viewer.out = str(_resolve_path(Path(viewer.out), base_dir))
    return viewer


def _resolve_required_path(data: dict[str, Any], section_name: str, base_dir: Path) -> Path:
    section = _required_section(data, section_name)
    path_value = section.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise CoderollError(f"{section_name}.path is required and must be a non-empty string")
    return _resolve_path(Path(path_value), base_dir)


def _resolve_path(path: Path, base_dir: Path) -> Path:
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CoderollError(f"{key} is required and must be a non-empty string")
    return value


def _optional_top_level_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CoderollError(f"{key} must be a non-empty string when set")
    return value.strip().lower()


def _runtime_eval_commands(runtime: Any) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    if runtime.default_build_command:
        commands.append(
            {
                "name": "typecheck",
                "command": runtime.default_build_command,
                "result_format": "exit_code",
            }
        )
    commands.append(
        {
            "name": "tests",
            "command": runtime.default_test_command,
            "result_format": runtime.result_format,
        }
    )
    return commands


def _required_section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise CoderollError(f"{key} section is required and must be a table/object")
    return value


def _optional_section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CoderollError(f"{key} section must be a table/object")
    return value


def _optional_str(section: dict[str, Any], key: str, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise CoderollError(f"{key} must be a non-empty string")
    return value


def _optional_str_or_none(section: dict[str, Any], key: str) -> str | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CoderollError(f"{key} must be a string when set")
    if not value.strip():
        return None
    return value


def _optional_bool(section: dict[str, Any], key: str, default: bool, label: str) -> bool:
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise CoderollError(f"{label} must be a boolean")
    return value


def _optional_positive_int(
    section: dict[str, Any],
    key: str,
    default: int,
    label: str,
) -> int:
    value = section.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise CoderollError(f"{label} must be a positive integer")
    return value


def _optional_str_list(
    section: dict[str, Any],
    key: str,
    default: list[str],
    label: str,
) -> list[str]:
    value = section.get(key, default)
    if not isinstance(value, list):
        raise CoderollError(f"{label} must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CoderollError(f"{label} must be a list of non-empty strings")
        result.append(item)
    return result
