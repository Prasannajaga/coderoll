from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from .errors import CandidateError
from .hashing import short_hash_text


@dataclass
class Candidate:
    code: str
    id: str = ""
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"cand_{short_hash_text(self.code)}"

    @classmethod
    def from_file(cls, path: str | Path) -> "Candidate":
        candidate_path = Path(path)
        if not candidate_path.exists():
            raise CandidateError(f"Candidate file does not exist: {candidate_path}")
        if not candidate_path.is_file():
            raise CandidateError(f"Candidate path is not a file: {candidate_path}")
        code = candidate_path.read_text(encoding="utf-8")
        return cls(
            id=f"cand_{short_hash_text(code)}",
            code=code,
            source="file",
            metadata={"path": str(candidate_path)},
        )

    @classmethod
    def from_jsonl(cls, path: str | Path) -> list["Candidate"]:
        candidate_path = Path(path)
        if not candidate_path.exists():
            raise CandidateError(f"Candidates JSONL file does not exist: {candidate_path}")

        candidates: list[Candidate] = []
        with candidate_path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CandidateError(
                        f"Invalid JSON on line {line_number} in {candidate_path}: {exc}"
                    ) from exc

                if not isinstance(item, dict):
                    raise CandidateError(
                        f"Line {line_number} in {candidate_path} must contain a JSON object"
                    )
                if "code" not in item:
                    raise CandidateError(
                        f"Line {line_number} in {candidate_path} is missing required field 'code'"
                    )

                code = str(item["code"])
                candidate_id = item.get("id")
                source = str(item.get("source", "manual"))
                metadata = item.get("metadata", {})
                if not isinstance(metadata, dict):
                    raise CandidateError(
                        f"Line {line_number} in {candidate_path} has non-object metadata"
                    )

                candidates.append(
                    cls(
                        id=str(candidate_id) if candidate_id else f"cand_{short_hash_text(code)}",
                        code=code,
                        source=source,
                        metadata=metadata,
                    )
                )

        return candidates

    @classmethod
    def from_string(cls, code: str, id: str | None = None) -> "Candidate":
        return cls(code=code, id=id or "", source="manual")
