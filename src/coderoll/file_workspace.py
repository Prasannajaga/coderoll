from pathlib import Path

from .candidate import Candidate
from .path_safety import safe_join


def write_candidate_to_workspace(candidate: Candidate, workspace_path: str | Path) -> None:
    workspace = Path(workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)
    for relative, content in candidate.files.items():
        target = safe_join(workspace, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
