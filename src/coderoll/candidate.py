from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from .errors import CandidateError
from .hashing import short_hash_text
from .path_safety import is_safe_relative_path


@dataclass
class Candidate:
    id: str = ""
    code: str | None = None
    tests: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Backward compatibility: Candidate("code") used to mean a single code candidate.
        if self.code is None and self.tests is None and not self.files and self.id:
            self.code = self.id
            self.id = ""

        if self.code is not None:
            self.code = str(self.code)
        if self.tests is not None:
            self.tests = str(self.tests)
        self.files = {str(path): str(content) for path, content in self.files.items()}
        for relative in self.files:
            if not is_safe_relative_path(relative):
                raise CandidateError(f"Unsafe candidate file path: {relative}")
        if not isinstance(self.metadata, dict):
            raise CandidateError("Candidate metadata must be an object")
        if not self.files and self.code is None and self.tests is None:
            raise CandidateError("Candidate must contain files, code, or tests")

        if not self.id:
            self.id = f"cand_{short_hash_text(self._identity_text())}"

    @property
    def mode(self) -> str:
        return "file"

    @classmethod
    def from_dict(cls, data: dict[str, Any], file_config: Any | None = None) -> "Candidate":
        if not isinstance(data, dict):
            raise CandidateError("Candidate record must be an object")
        config = _file_config(file_config)
        raw_files = data.get("files")
        code = data.get("code")
        tests = data.get("tests")
        if raw_files is None and code is None and tests is None:
            raise CandidateError("Candidate record must contain files, code, or tests")

        files: dict[str, str] = {}
        if raw_files is not None:
            if not isinstance(raw_files, dict) or not raw_files:
                raise CandidateError("Candidate files must be a non-empty object")
            files.update({str(path): str(content) for path, content in raw_files.items()})
        if code is not None:
            files[config.code_file] = str(code)
        if tests is not None:
            files[config.test_file] = str(tests)

        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            raise CandidateError("Candidate metadata must be an object")

        return cls(
            id=str(data.get("id", "")),
            code=str(code) if code is not None else None,
            tests=str(tests) if tests is not None else None,
            files=files,
            source=str(data.get("source", "manual")),
            metadata=metadata,
        )

    @classmethod
    def from_file(cls, path: str | Path, entry_file: str | None = None) -> "Candidate":
        candidate_path = Path(path)
        if not candidate_path.exists():
            raise CandidateError(f"Candidate file does not exist: {candidate_path}")
        if not candidate_path.is_file():
            raise CandidateError(f"Candidate path is not a file: {candidate_path}")
        code = candidate_path.read_text(encoding="utf-8")
        return cls(
            id=f"cand_{short_hash_text(code)}",
            code=code,
            files={entry_file or "solution.py": code},
            source="file",
            metadata={"path": str(candidate_path), "entry_file": entry_file},
        )

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        file_config: Any | None = None,
    ) -> list["Candidate"]:
        candidate_path = Path(path)
        if not candidate_path.exists():
            raise CandidateError(f"Candidate JSON file does not exist: {candidate_path}")
        if not candidate_path.is_file():
            raise CandidateError(f"Candidate JSON path is not a file: {candidate_path}")
        try:
            data = json.loads(candidate_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CandidateError(f"Invalid JSON in {candidate_path}: {exc}") from exc

        if isinstance(data, dict):
            return [cls.from_dict(data, file_config)]
        if isinstance(data, list):
            candidates: list[Candidate] = []
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    raise CandidateError(f"Item {index} in {candidate_path} must be an object")
                candidates.append(cls.from_dict(item, file_config))
            return candidates
        raise CandidateError(f"Candidate JSON root must be an object or array in {candidate_path}")

    @classmethod
    def from_jsonl(
        cls,
        path: str | Path,
        file_config: Any | None = None,
    ) -> list["Candidate"]:
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
                candidates.append(cls.from_dict(item, file_config))
        return candidates

    @classmethod
    def load_many(
        cls,
        candidates_config: Any,
        file_config: Any | None = None,
    ) -> list["Candidate"]:
        type_key = str(candidates_config.type).strip().lower()
        if type_key == "json":
            return cls.from_json(candidates_config.path, file_config)
        if type_key == "jsonl":
            return cls.from_jsonl(candidates_config.path, file_config)
        raise CandidateError("candidates.type must be one of: json, jsonl")

    @classmethod
    def from_string(cls, code: str, id: str | None = None) -> "Candidate":
        return cls(code=code, files={"solution.py": code}, id=id or "", source="manual")

    def _identity_text(self) -> str:
        if self.files:
            return json.dumps(self.files, sort_keys=True, ensure_ascii=False)
        return "\n".join(part for part in [self.code, self.tests] if part)


@dataclass
class _DefaultFileConfig:
    code_file: str = "solution.py"
    test_file: str = "test_solution.py"


def _file_config(file_config: Any | None) -> Any:
    return file_config if file_config is not None else _DefaultFileConfig()
