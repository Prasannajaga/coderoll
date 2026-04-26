from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from .errors import CoderollError
from .workspace import DEFAULT_EXCLUDE, WorkspaceConfig


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
class CandidatesConfig:
    type: str
    path: Path
    mode: str
    entry_file: str | None = None


@dataclass
class SetupConfig:
    commands: list[str]
    allow_candidate_dependencies: bool = False
    dependency_install_timeout: int | None = None


@dataclass
class EvalCommandConfig:
    command: str
    name: str | None = None
    result_format: str | None = None


@dataclass
class EvalConfig:
    commands: list[EvalCommandConfig]
    result_format: str = "exit_code"
    stop_on_first_failure: bool = False
    score_strategy: str = "weighted"


@dataclass
class RunConfig:
    id: str
    task_path: Path | None
    candidates_path: Path
    output_path: Path
    sandbox: SandboxConfig
    runner: RunnerConfig
    viewer: ViewerConfig
    raw: dict[str, Any]
    workspace: WorkspaceConfig
    candidates: CandidatesConfig
    setup: SetupConfig
    eval: EvalConfig
    base_dir: Path


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
    workspace = _normalize_workspace(data, base_dir)
    candidates = _normalize_candidates(data, base_dir)
    setup = _normalize_setup(data)
    eval_config = _normalize_eval(data)
    output_path = _normalize_output_path(data, base_dir)

    task_path = _resolve_required_path(data, "task", base_dir) if "task" in data else None
    candidates_path = candidates.path

    if task_path is not None and not task_path.exists():
        raise CoderollError(f"Task path does not exist: {task_path}")
    if workspace.path is not None and not workspace.path.exists():
        raise CoderollError(f"Workspace path does not exist: {workspace.path}")
    if not candidates_path.exists():
        raise CoderollError(f"Candidates path does not exist: {candidates_path}")

    runner_section = _optional_section(data, "runner")
    workers = runner_section.get("workers", 1)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise CoderollError("runner.workers must be an integer >= 1")
    runner = RunnerConfig(workers=workers)

    sandbox_section = _optional_section(data, "sandbox")
    sandbox = SandboxConfig(
        image=_optional_str_or_none(sandbox_section, "image"),
        timeout=_optional_positive_int(sandbox_section, "timeout", 5, "sandbox.timeout"),
        memory=_optional_str(sandbox_section, "memory", "256m"),
        cpus=_optional_str(sandbox_section, "cpus", "1"),
        pids_limit=_optional_positive_int(
            sandbox_section, "pids_limit", 128, "sandbox.pids_limit"
        ),
        network=_optional_bool(sandbox_section, "network", False, "sandbox.network"),
    )

    viewer_section = _optional_section(data, "viewer")
    viewer = ViewerConfig(
        enabled=_optional_bool(viewer_section, "enabled", False, "viewer.enabled"),
        out=_optional_str_or_none(viewer_section, "out"),
        open=_optional_bool(viewer_section, "open", True, "viewer.open"),
    )
    if viewer.out is not None:
        viewer.out = str(_resolve_path(Path(viewer.out), base_dir))

    return RunConfig(
        id=run_id,
        task_path=task_path,
        candidates_path=candidates_path,
        output_path=output_path,
        sandbox=sandbox,
        runner=runner,
        viewer=viewer,
        raw=dict(data),
        workspace=workspace,
        candidates=candidates,
        setup=setup,
        eval=eval_config,
        base_dir=base_dir,
    )


def _normalize_workspace(data: dict[str, Any], base_dir: Path) -> WorkspaceConfig:
    if "workspace" not in data:
        task_path = _resolve_required_path(data, "task", base_dir)
        return WorkspaceConfig(mode="project", path=task_path)
    section = _required_section(data, "workspace")
    mode = _optional_str(section, "mode", "scratch").strip().lower()
    if mode not in {"scratch", "project"}:
        raise CoderollError("workspace.mode must be one of: scratch, project")
    path = _optional_str_or_none(section, "path")
    resolved = _resolve_path(Path(path), base_dir) if path is not None else None
    if mode == "project" and resolved is None:
        raise CoderollError("workspace.path is required when workspace.mode=project")
    include = _optional_str_list(section, "include", ["**/*"], "workspace.include")
    exclude = _optional_str_list(section, "exclude", list(DEFAULT_EXCLUDE), "workspace.exclude")
    return WorkspaceConfig(mode=mode, path=resolved, include=include, exclude=exclude)


def _normalize_candidates(data: dict[str, Any], base_dir: Path) -> CandidatesConfig:
    section = _required_section(data, "candidates")
    path_value = section.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise CoderollError("candidates.path is required and must be a non-empty string")
    path = _resolve_path(Path(path_value), base_dir)
    type_value = str(section.get("type", "jsonl")).strip().lower()
    if type_value not in {"json", "jsonl", "directory"}:
        raise CoderollError("candidates.type must be one of: json, jsonl, directory")
    mode = str(section.get("mode", "file" if type_value != "directory" else "directory")).strip().lower()
    if mode not in {"file", "files", "directory"}:
        raise CoderollError("candidates.mode must be one of: file, files, directory")
    entry_file = _optional_str_or_none(section, "entry_file")
    return CandidatesConfig(type=type_value, path=path, mode=mode, entry_file=entry_file)


def _normalize_setup(data: dict[str, Any]) -> SetupConfig:
    section = _optional_section(data, "setup")
    timeout = section.get("dependency_install_timeout")
    if timeout is not None and (
        not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0
    ):
        raise CoderollError("setup.dependency_install_timeout must be a positive integer")
    return SetupConfig(
        commands=_optional_str_list(section, "commands", [], "setup.commands"),
        allow_candidate_dependencies=_optional_bool(
            section,
            "allow_candidate_dependencies",
            False,
            "setup.allow_candidate_dependencies",
        ),
        dependency_install_timeout=timeout,
    )


def _normalize_eval(data: dict[str, Any]) -> EvalConfig:
    section = _optional_section(data, "eval")
    raw_commands = section.get("commands")
    if raw_commands is None and "task" in data:
        raw_commands = ["__legacy_task_command__"]
    if raw_commands is None:
        raise CoderollError("eval.commands is required")
    if not isinstance(raw_commands, list) or not raw_commands:
        raise CoderollError("eval.commands must be a non-empty list")
    commands: list[EvalCommandConfig] = []
    for index, item in enumerate(raw_commands):
        if isinstance(item, str):
            if not item.strip():
                raise CoderollError(f"eval.commands[{index}] must not be empty")
            commands.append(EvalCommandConfig(command=item))
        elif isinstance(item, dict):
            command = item.get("command")
            if not isinstance(command, str) or not command.strip():
                raise CoderollError(f"eval.commands[{index}].command must be a non-empty string")
            name = item.get("name")
            result_format = item.get("result_format")
            normalized_format = (
                str(result_format).strip().lower() if result_format is not None else None
            )
            if normalized_format is not None and normalized_format not in {
                "junit",
                "tap",
                "exit_code",
            }:
                raise CoderollError(
                    f"eval.commands[{index}].result_format must be one of: junit, tap, exit_code"
                )
            commands.append(
                EvalCommandConfig(
                    command=command,
                    name=str(name) if name is not None else None,
                    result_format=normalized_format,
                )
            )
        else:
            raise CoderollError(f"eval.commands[{index}] must be a string or object")
    result_format = str(section.get("result_format", "exit_code")).strip().lower()
    if result_format not in {"junit", "tap", "exit_code"}:
        raise CoderollError("eval.result_format must be one of: junit, tap, exit_code")
    strategy = str(section.get("score_strategy", "weighted")).strip().lower()
    if strategy not in {"weighted", "command_average", "tests_only"}:
        raise CoderollError("eval.score_strategy must be one of: weighted, command_average, tests_only")
    return EvalConfig(
        commands=commands,
        result_format=result_format,
        stop_on_first_failure=_optional_bool(
            section,
            "stop_on_first_failure",
            False,
            "eval.stop_on_first_failure",
        ),
        score_strategy=strategy,
    )


def _normalize_output_path(data: dict[str, Any], base_dir: Path) -> Path:
    return _resolve_required_path(data, "output", base_dir)


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
    if not isinstance(value, str):
        raise CoderollError(f"{key} must be a string")
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
