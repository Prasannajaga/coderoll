from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSpec:
    language: str
    default_image: str
    default_entry_file: str
    default_test_file: str
    default_test_command: str
    default_build_command: str | None = None
    result_format: str = "exit_code"
