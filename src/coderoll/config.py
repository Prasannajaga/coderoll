from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from .errors import CoderollError


@dataclass
class SandboxConfig:
    image: str = "coderoll-python:3.11"
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
    task_path: Path
    candidates_path: Path
    output_path: Path
    sandbox: SandboxConfig
    runner: RunnerConfig
    viewer: ViewerConfig
    raw: dict[str, Any]


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
    task_path = _resolve_required_path(data, "task", base_dir)
    candidates_path = _resolve_required_path(data, "candidates", base_dir)
    output_path = _resolve_required_path(data, "output", base_dir)

    if not task_path.exists():
        raise CoderollError(f"Task path does not exist: {task_path}")
    if not candidates_path.exists():
        raise CoderollError(f"Candidates path does not exist: {candidates_path}")

    runner_section = _optional_section(data, "runner")
    workers = runner_section.get("workers", 1)
    if not isinstance(workers, int) or workers < 1:
        raise CoderollError("runner.workers must be an integer >= 1")
    runner = RunnerConfig(workers=workers)

    sandbox_section = _optional_section(data, "sandbox")
    sandbox = SandboxConfig(
        image=_optional_str(sandbox_section, "image", "coderoll-python:3.11"),
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
    )


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
    if not isinstance(value, int) or value <= 0:
        raise CoderollError(f"{label} must be a positive integer")
    return value
