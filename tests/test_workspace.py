from pathlib import Path

from coderoll.candidate import Candidate
from coderoll.workspace import (
    WorkspaceConfig,
    copy_project_workspace,
    prepare_workspace,
    safe_write_candidate_files,
)


def test_scratch_workspace(tmp_path: Path) -> None:
    workspace = prepare_workspace(WorkspaceConfig(mode="scratch"), tmp_path)

    assert workspace.exists()
    assert list(workspace.iterdir()) == []


def test_project_workspace_copies_and_excludes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("x = 1", encoding="utf-8")
    (project / ".git").mkdir()
    (project / ".git" / "config").write_text("secret", encoding="utf-8")
    (project / "node_modules").mkdir()
    (project / "node_modules" / "pkg.js").write_text("x", encoding="utf-8")

    workspace = prepare_workspace(WorkspaceConfig(mode="project", path=project), tmp_path / "tmp")

    assert (workspace / "app.py").exists()
    assert not (workspace / ".git" / "config").exists()
    assert not (workspace / "node_modules" / "pkg.js").exists()


def test_candidate_files_overlay_project_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "solution.py").write_text("old", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    copy_project_workspace(project, workspace)

    safe_write_candidate_files(workspace, Candidate(files={"solution.py": "new"}))

    assert (workspace / "solution.py").read_text(encoding="utf-8") == "new"
