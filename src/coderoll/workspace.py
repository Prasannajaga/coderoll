from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
import shutil

from .candidate import Candidate
from .errors import CoderollError
from .path_safety import safe_join


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


@dataclass
class WorkspaceConfig:
    mode: str
    path: Path | None = None
    include: list[str] = field(default_factory=lambda: ["**/*"])
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE))


def prepare_workspace(config: WorkspaceConfig, temp_dir: str | Path) -> Path:
    workspace = Path(temp_dir) / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    if config.mode == "scratch":
        return workspace
    if config.mode == "project":
        if config.path is None:
            raise CoderollError("workspace.path is required when workspace.mode=project")
        copy_project_workspace(config.path, workspace, config.include, config.exclude)
        return workspace
    raise CoderollError("workspace.mode must be one of: scratch, project")


def copy_project_workspace(
    src: str | Path,
    dest: str | Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> None:
    source_root = Path(src)
    target_root = Path(dest)
    if not source_root.exists():
        raise CoderollError(f"Workspace path does not exist: {source_root}")
    if not source_root.is_dir():
        raise CoderollError(f"Workspace path is not a directory: {source_root}")

    include_patterns = include or ["**/*"]
    exclude_patterns = exclude or list(DEFAULT_EXCLUDE)
    for source in source_root.rglob("*"):
        if source.is_symlink():
            continue
        if source.is_dir():
            continue
        relative = source.relative_to(source_root)
        rel = relative.as_posix()
        if not _included(rel, include_patterns):
            continue
        if _excluded(rel, relative.parts, exclude_patterns):
            continue
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def safe_write_candidate_files(
    workspace: str | Path,
    candidate: Candidate,
    entry_file: str | None = None,
) -> None:
    root = Path(workspace)
    if candidate.code is not None:
        if not entry_file:
            raise CoderollError("entry_file is required for single-file code candidates")
        target = safe_join(root, entry_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(candidate.code, encoding="utf-8")
        return

    for relative, content in candidate.files.items():
        target = safe_join(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def safe_copy_candidate_directory(
    candidate_dir: str | Path,
    workspace: str | Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> None:
    copy_project_workspace(candidate_dir, workspace, include or ["**/*"], exclude or list(DEFAULT_EXCLUDE))


def _included(rel: str, patterns: list[str]) -> bool:
    return any(pattern == "**/*" or fnmatch(rel, pattern) for pattern in patterns)


def _excluded(rel: str, parts: tuple[str, ...], patterns: list[str]) -> bool:
    excluded_dirs = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        ".coderoll",
    }
    if any(part in excluded_dirs for part in parts):
        return True
    return any(fnmatch(rel, pattern) for pattern in patterns)
