from pathlib import Path

from coderoll.candidate import Candidate


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
