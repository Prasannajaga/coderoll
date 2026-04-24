from pathlib import Path
import json

from ..errors import StoreError
from ..result import RunRecord


class JsonlStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: RunRecord) -> None:
        self.append_many([record])

    def append_many(self, records: list[RunRecord]) -> None:
        if not records:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record.to_dict(), ensure_ascii=False))
                    handle.write("\n")
        except OSError as exc:
            raise StoreError(f"Failed to write JSONL store {self.path}: {exc}") from exc

    def read_all(self) -> list[RunRecord]:
        if not self.path.exists():
            return []

        records: list[RunRecord] = []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise StoreError(
                            f"Invalid JSON in {self.path} on line {line_number}: {exc}"
                        ) from exc
                    if not isinstance(item, dict):
                        raise StoreError(
                            f"Invalid JSON object in {self.path} on line {line_number}"
                        )
                    records.append(RunRecord.from_dict(item))
        except OSError as exc:
            raise StoreError(f"Failed to read JSONL store {self.path}: {exc}") from exc

        return records
