from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from .errors import TaskError
from .runtimes import get_runtime


DEFAULT_TIMEOUT = 5


@dataclass
class Task:
    id: str
    root: Path
    prompt: str
    language: str
    image: str | None
    entry_file: str
    test_file: str
    build_command: str | None
    test_command: str
    result_format: str
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
        language = "python"
        timeout = DEFAULT_TIMEOUT
        config: dict[str, Any] = {}
        metadata: dict[str, Any] = {}

        config_path = root / "task.toml"
        if config_path.exists():
            try:
                with config_path.open("rb") as handle:
                    config = tomllib.load(handle)
            except tomllib.TOMLDecodeError as exc:
                raise TaskError(f"Invalid TOML in {config_path}: {exc}") from exc

            timeout_value = config.get("timeout", timeout)
            if not isinstance(timeout_value, int) or isinstance(timeout_value, bool):
                raise TaskError("task.toml field 'timeout' must be an integer")
            timeout = timeout_value
            task_id = str(config.get("id", task_id))
            language = str(config.get("language", language)).strip().lower() or "python"

            meta_value = config.get("metadata")
            if meta_value is not None and not isinstance(meta_value, dict):
                raise TaskError("task.toml field 'metadata' must be a table")
            if isinstance(meta_value, dict):
                metadata.update(meta_value)

            known = {
                "id",
                "language",
                "image",
                "entry_file",
                "test_file",
                "build_command",
                "test_command",
                "result_format",
                "timeout",
                "metadata",
            }
            for key, value in config.items():
                if key not in known:
                    metadata[key] = value

        try:
            runtime = get_runtime(language)
        except Exception as exc:  # noqa: BLE001
            raise TaskError(str(exc)) from exc

        image = _optional_config_str(config, "image", runtime.default_image)
        entry_file = _optional_config_str(config, "entry_file", runtime.default_entry_file) or runtime.default_entry_file
        test_file = _optional_config_str(config, "test_file", runtime.default_test_file) or runtime.default_test_file
        build_command = _optional_config_str(
            config,
            "build_command",
            runtime.default_build_command,
        )
        test_command = _optional_config_str(
            config,
            "test_command",
            runtime.default_test_command,
        ) or runtime.default_test_command
        result_format = _optional_config_str(
            config,
            "result_format",
            runtime.result_format,
        ) or runtime.result_format

        test_path = root / test_file
        if not test_path.exists():
            raise TaskError(f"Missing test file: {test_path}")

        return cls(
            id=task_id,
            root=root,
            prompt=prompt,
            language=language,
            image=image,
            entry_file=entry_file,
            test_file=test_file,
            build_command=build_command,
            test_command=test_command,
            result_format=result_format,
            timeout=timeout,
            metadata=metadata,
        )


def _optional_config_str(
    config: dict[str, Any],
    key: str,
    default: str | None,
) -> str | None:
    value = config.get(key, default)
    if value is None:
        return None
    text = str(value)
    return text if text.strip() else default
