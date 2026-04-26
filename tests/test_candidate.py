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
    assert candidates[0].files == {"solution.py": "def solution(x): return x + 1"}
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
    assert candidates[0].files == {"solution.py": "def solution(x): return x"}


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
    assert candidates[0].mode == "file"


def test_candidate_code_tests_shortcut() -> None:
    candidate = Candidate.from_dict(
        {
            "id": "shortcut",
            "code": "def add_one(x): return x + 1",
            "tests": "from solution import add_one",
        },
    )

    assert candidate.files == {
        "solution.py": "def add_one(x): return x + 1",
        "test_solution.py": "from solution import add_one",
    }


def test_candidate_code_tests_custom_files() -> None:
    class FileConfig:
        code_file = "src/main.py"
        test_file = "tests/test_main.py"

    candidate = Candidate.from_dict(
        {
            "code": "x = 1",
            "tests": "def test_x(): assert True",
        },
        FileConfig(),
    )

    assert candidate.files == {
        "src/main.py": "x = 1",
        "tests/test_main.py": "def test_x(): assert True",
    }


def test_candidate_generated_id_for_files() -> None:
    candidate = Candidate(files={"solution.py": "x = 1"})

    assert candidate.id.startswith("cand_")


def test_candidate_rejects_unsafe_file_path() -> None:
    with pytest.raises(CandidateError):
        Candidate(files={"../solution.py": "x = 1"})
