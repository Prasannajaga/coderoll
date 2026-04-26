from pathlib import Path

from .errors import CandidateError


def is_safe_relative_path(path: str) -> bool:
    if not isinstance(path, str):
        return False
    if not path.strip():
        return False
    if path.startswith("~"):
        return False
    candidate = Path(path)
    if candidate.is_absolute():
        return False
    return ".." not in candidate.parts


def safe_join(base: Path, relative: str) -> Path:
    if not is_safe_relative_path(relative):
        raise CandidateError(f"Unsafe relative path: {relative}")
    target = base / relative
    ensure_within_base(base, target)
    return target


def ensure_within_base(base: Path, target: Path) -> None:
    base_resolved = base.resolve()
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise CandidateError(f"Path escapes workspace: {target}") from exc
