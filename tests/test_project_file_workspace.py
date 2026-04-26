from pathlib import Path

import pytest

from coderoll.candidate import Candidate
from coderoll.config import ProjectConfig
from coderoll.errors import CandidateError
from coderoll.file_workspace import write_candidate_to_workspace
from coderoll.project import copy_project_to_workspace, iter_project_files


def test_project_copy_works_and_excludes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("x = 1", encoding="utf-8")
    (project / ".git").mkdir()
    (project / ".git" / "config").write_text("secret", encoding="utf-8")
    (project / "node_modules").mkdir()
    (project / "node_modules" / "pkg.js").write_text("x", encoding="utf-8")
    workspace = tmp_path / "workspace"

    copy_project_to_workspace(ProjectConfig(path=project), workspace)

    assert (workspace / "app.py").read_text(encoding="utf-8") == "x = 1"
    assert not (workspace / ".git" / "config").exists()
    assert not (workspace / "node_modules" / "pkg.js").exists()
    assert (project / "app.py").read_text(encoding="utf-8") == "x = 1"


def test_project_include_filter(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("x = 1", encoding="utf-8")
    (project / "README.md").write_text("docs", encoding="utf-8")

    files = list(iter_project_files(project, ["*.py"], []))

    assert [relative.as_posix() for _, relative in files] == ["app.py"]


def test_write_candidate_to_empty_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    candidate = Candidate(files={"src/solution.py": "x = 1"})

    write_candidate_to_workspace(candidate, workspace)

    assert (workspace / "src" / "solution.py").read_text(encoding="utf-8") == "x = 1"


def test_write_candidate_rejects_unsafe_paths(tmp_path: Path) -> None:
    with pytest.raises(CandidateError):
        Candidate(files={"../solution.py": "x = 1"})
