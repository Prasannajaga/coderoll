from pathlib import Path

import pytest

from coderoll.candidate import Candidate
from coderoll.errors import CandidateError


def test_candidate_from_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "candidates.jsonl"
    path.write_text(
        '{"id":"given", "code":"def solution(x): return x + 1", "source":"model"}\n'
        '{"code":"def solution(x): return x"}\n',
        encoding="utf-8",
    )

    candidates = Candidate.from_jsonl(path)

    assert len(candidates) == 2
    assert candidates[0].id == "given"
    assert candidates[0].source == "model"
    assert candidates[1].id.startswith("cand_")


def test_candidate_from_file(tmp_path: Path) -> None:
    path = tmp_path / "solution.py"
    path.write_text("def solution(x):\n    return x + 1\n", encoding="utf-8")

    candidate = Candidate.from_file(path)

    assert candidate.code.startswith("def solution")
    assert candidate.id.startswith("cand_")
    assert candidate.source == "file"


def test_candidate_from_json_single_object(tmp_path: Path) -> None:
    path = tmp_path / "candidate.json"
    path.write_text('{"id":"one","code":"def solution(x): return x"}', encoding="utf-8")

    candidates = Candidate.from_json(path)

    assert len(candidates) == 1
    assert candidates[0].id == "one"
    assert candidates[0].code == "def solution(x): return x"


def test_candidate_from_json_array(tmp_path: Path) -> None:
    path = tmp_path / "candidate.json"
    path.write_text(
        '[{"id":"a","code":"a = 1"},{"id":"b","code":"b = 2"}]',
        encoding="utf-8",
    )

    candidates = Candidate.from_json(path)

    assert [candidate.id for candidate in candidates] == ["a", "b"]


def test_candidate_files_record(tmp_path: Path) -> None:
    path = tmp_path / "candidates.jsonl"
    path.write_text('{"id":"multi","files":{"src/solution.py":"x = 1"}}\n', encoding="utf-8")

    candidates = Candidate.from_jsonl(path)

    assert candidates[0].files == {"src/solution.py": "x = 1"}
    assert candidates[0].mode == "files"


def test_candidate_directory(tmp_path: Path) -> None:
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "solution.py").write_text("x = 1", encoding="utf-8")

    candidate = Candidate.from_directory(candidate_dir)

    assert candidate.directory == candidate_dir
    assert candidate.id.startswith("cand_")
    assert candidate.mode == "directory"


def test_candidate_generated_id_for_files() -> None:
    candidate = Candidate(files={"solution.py": "x = 1"})

    assert candidate.id.startswith("cand_")


def test_candidate_rejects_unsafe_file_path() -> None:
    with pytest.raises(CandidateError):
        Candidate(files={"../solution.py": "x = 1"})
