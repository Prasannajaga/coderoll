from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable
import shutil

from .config import ProjectConfig
from .errors import CoderollError


EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    ".coderoll",
}


def copy_project_to_workspace(project_config: ProjectConfig, workspace_path: str | Path) -> None:
    dest = Path(workspace_path)
    dest.mkdir(parents=True, exist_ok=True)
    for source, relative in iter_project_files(
        project_config.path,
        project_config.include,
        project_config.exclude,
    ):
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def iter_project_files(
    src: str | Path,
    include: list[str],
    exclude: list[str],
) -> Iterable[tuple[Path, Path]]:
    root = Path(src)
    if not root.exists():
        raise CoderollError(f"project.path does not exist: {root}")
    if not root.is_dir():
        raise CoderollError(f"project.path must be a directory: {root}")

    for source in sorted(root.rglob("*")):
        if source.is_symlink() or source.is_dir():
            continue
        relative = source.relative_to(root)
        rel = relative.as_posix()
        if _excluded(rel, relative.parts, exclude):
            continue
        if not _included(rel, include):
            continue
        yield source, relative


def _included(rel: str, patterns: list[str]) -> bool:
    return any(pattern == "**/*" or fnmatch(rel, pattern) for pattern in patterns)


def _excluded(rel: str, parts: tuple[str, ...], patterns: list[str]) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return True
    return any(fnmatch(rel, pattern) for pattern in patterns)
