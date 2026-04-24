from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from .errors import TaskError


DEFAULT_ENTRY_FILE = "solution.py"
DEFAULT_TEST_FILE = "test_solution.py"
DEFAULT_TEST_COMMAND = "python -m pytest -q"
DEFAULT_TIMEOUT = 5


@dataclass
class Task:
    id: str
    root: Path
    prompt: str
    entry_file: str
    test_file: str
    test_command: str
    timeout: int
    metadata: dict[str, Any]

    @property
    def test_path(self) -> Path:
        return self.root / self.test_file

    @property
    def prompt_path(self) -> Path:
        return self.root / "prompt.txt"

    @property
    def config_path(self) -> Path:
        return self.root / "task.toml"

    @classmethod
    def from_dir(cls, path: str | Path) -> "Task":
        root = Path(path)
        if not root.exists():
            raise TaskError(f"Task directory does not exist: {root}")
        if not root.is_dir():
            raise TaskError(f"Task path is not a directory: {root}")

        prompt_path = root / "prompt.txt"
        if not prompt_path.exists():
            raise TaskError(f"Missing prompt file: {prompt_path}")
        prompt = prompt_path.read_text(encoding="utf-8")

        task_id = root.name
        entry_file = DEFAULT_ENTRY_FILE
        test_file = DEFAULT_TEST_FILE
        test_command = DEFAULT_TEST_COMMAND
        timeout = DEFAULT_TIMEOUT
        metadata: dict[str, Any] = {}

        config_path = root / "task.toml"
        if config_path.exists():
            try:
                with config_path.open("rb") as handle:
                    config = tomllib.load(handle)
            except tomllib.TOMLDecodeError as exc:
                raise TaskError(f"Invalid TOML in {config_path}: {exc}") from exc

            task_id = str(config.get("id", task_id))
            entry_file = str(config.get("entry_file", entry_file))
            test_file = str(config.get("test_file", test_file))
            test_command = str(config.get("test_command", test_command))

            timeout_value = config.get("timeout", timeout)
            if not isinstance(timeout_value, int):
                raise TaskError("task.toml field 'timeout' must be an integer")
            timeout = timeout_value

            meta_value = config.get("metadata")
            if meta_value is not None and not isinstance(meta_value, dict):
                raise TaskError("task.toml field 'metadata' must be a table")
            if isinstance(meta_value, dict):
                metadata.update(meta_value)

            known = {
                "id",
                "entry_file",
                "test_file",
                "test_command",
                "timeout",
                "metadata",
            }
            for key, value in config.items():
                if key not in known:
                    metadata[key] = value

        test_path = root / test_file
        if not test_path.exists():
            raise TaskError(f"Missing test file: {test_path}")

        return cls(
            id=task_id,
            root=root,
            prompt=prompt,
            entry_file=entry_file,
            test_file=test_file,
            test_command=test_command,
            timeout=timeout,
            metadata=metadata,
        )
