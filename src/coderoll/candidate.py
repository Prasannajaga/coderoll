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
    files: dict[str, str] = field(default_factory=dict)
    directory: Path | None = None
    dependencies: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Backward compatibility: Candidate("code") used to mean a single code candidate.
        if self.code is None and not self.files and self.directory is None and self.id:
            self.code = self.id
            self.id = ""

        modes = sum(
            [
                self.code is not None,
                bool(self.files),
                self.directory is not None,
            ]
        )
        if modes != 1:
            raise CandidateError("Candidate must have exactly one of code, files, or directory")

        if self.code is not None:
            self.code = str(self.code)
        self.files = {str(path): str(content) for path, content in self.files.items()}
        for relative in self.files:
            if not is_safe_relative_path(relative):
                raise CandidateError(f"Unsafe candidate file path: {relative}")
        if self.directory is not None:
            self.directory = Path(self.directory)
            if not self.directory.exists():
                raise CandidateError(f"Candidate directory does not exist: {self.directory}")
            if not self.directory.is_dir():
                raise CandidateError(f"Candidate path is not a directory: {self.directory}")
        if not isinstance(self.dependencies, dict):
            raise CandidateError("Candidate dependencies must be an object")
        if not isinstance(self.metadata, dict):
            raise CandidateError("Candidate metadata must be an object")

        if not self.id:
            self.id = f"cand_{short_hash_text(self._identity_text())}"

    @property
    def mode(self) -> str:
        if self.directory is not None:
            return "directory"
        if self.files:
            return "files"
        return "file"

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
            source="file",
            metadata={"path": str(candidate_path), "entry_file": entry_file},
        )

    @classmethod
    def from_json(cls, path: str | Path) -> list["Candidate"]:
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
            return [_candidate_from_record(data, f"{candidate_path}")]
        if isinstance(data, list):
            candidates: list[Candidate] = []
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    raise CandidateError(f"Item {index} in {candidate_path} must be an object")
                candidates.append(_candidate_from_record(item, f"{candidate_path}#{index}"))
            return candidates
        raise CandidateError(f"Candidate JSON root must be an object or array in {candidate_path}")

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
                candidates.append(_candidate_from_record(item, f"{candidate_path}:{line_number}"))

        return candidates

    @classmethod
    def from_directory(cls, path: str | Path) -> "Candidate":
        candidate_path = Path(path)
        return cls(
            id=f"cand_{short_hash_text(_directory_identity(candidate_path))}",
            directory=candidate_path,
            source="directory",
            metadata={"path": str(candidate_path)},
        )

    @classmethod
    def load_many(
        cls,
        path: str | Path,
        type: str,
        mode: str,
        entry_file: str | None = None,
    ) -> list["Candidate"]:
        type_key = type.strip().lower()
        mode_key = mode.strip().lower()
        candidate_path = Path(path)

        if type_key == "json":
            candidates = cls.from_json(candidate_path)
        elif type_key == "jsonl":
            candidates = cls.from_jsonl(candidate_path)
        elif type_key == "directory":
            candidates = [cls.from_directory(candidate_path)]
        else:
            raise CandidateError("candidates.type must be one of: json, jsonl, directory")

        if mode_key == "file":
            for candidate in candidates:
                if candidate.code is None:
                    raise CandidateError("candidates.mode=file requires candidate records with code")
        elif mode_key == "files":
            for candidate in candidates:
                if not candidate.files and candidate.code is None:
                    raise CandidateError("candidates.mode=files requires files or code records")
        elif mode_key == "directory":
            for candidate in candidates:
                if candidate.directory is None:
                    raise CandidateError("candidates.mode=directory requires a directory candidate")
        else:
            raise CandidateError("candidates.mode must be one of: file, files, directory")

        for candidate in candidates:
            if entry_file is not None:
                candidate.metadata.setdefault("entry_file", entry_file)
            candidate.metadata.setdefault("candidate_mode", mode_key)
        return candidates

    @classmethod
    def from_string(cls, code: str, id: str | None = None) -> "Candidate":
        return cls(code=code, id=id or "", source="manual")

    def _identity_text(self) -> str:
        if self.code is not None:
            return self.code
        if self.files:
            return json.dumps(self.files, sort_keys=True, ensure_ascii=False)
        if self.directory is not None:
            return _directory_identity(self.directory)
        return ""


def _candidate_from_record(item: dict[str, Any], source_label: str) -> Candidate:
    has_code = "code" in item
    has_files = "files" in item
    has_directory = "directory" in item
    if sum([has_code, has_files, has_directory]) != 1:
        raise CandidateError(
            f"Candidate record {source_label} must contain exactly one of code, files, or directory"
        )

    metadata = item.get("metadata", {})
    if not isinstance(metadata, dict):
        raise CandidateError(f"Candidate record {source_label} has non-object metadata")
    dependencies = item.get("dependencies", {})
    if dependencies is None:
        dependencies = {}
    if not isinstance(dependencies, dict):
        raise CandidateError(f"Candidate record {source_label} has non-object dependencies")

    files: dict[str, str] = {}
    if has_files:
        raw_files = item["files"]
        if not isinstance(raw_files, dict) or not raw_files:
            raise CandidateError(f"Candidate record {source_label} files must be a non-empty object")
        files = {str(path): str(content) for path, content in raw_files.items()}

    directory = Path(str(item["directory"])) if has_directory else None
    return Candidate(
        id=str(item.get("id", "")),
        code=str(item["code"]) if has_code else None,
        files=files,
        directory=directory,
        dependencies=dependencies,
        source=str(item.get("source", "manual")),
        metadata=metadata,
    )


def _directory_identity(path: Path) -> str:
    if not path.exists():
        return str(path)
    parts: list[str] = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            rel = item.relative_to(path).as_posix()
            try:
                content = item.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = item.read_bytes().hex()
            parts.append(f"{rel}:{short_hash_text(content)}")
    return "\n".join(parts) or str(path)
