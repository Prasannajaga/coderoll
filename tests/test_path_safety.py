from pathlib import Path

import pytest

from coderoll.errors import CandidateError
from coderoll.path_safety import is_safe_relative_path, safe_join


def test_rejects_absolute_paths() -> None:
    assert is_safe_relative_path("/tmp/x") is False


def test_rejects_parent_segments() -> None:
    assert is_safe_relative_path("../x") is False
    assert is_safe_relative_path("a/../x") is False


def test_rejects_home_and_empty_paths() -> None:
    assert is_safe_relative_path("~/x") is False
    assert is_safe_relative_path("") is False


def test_safe_join_remains_inside_workspace(tmp_path: Path) -> None:
    joined = safe_join(tmp_path, "src/solution.py")

    assert joined == tmp_path / "src" / "solution.py"


def test_safe_join_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(CandidateError):
        safe_join(tmp_path, "../escape.py")
