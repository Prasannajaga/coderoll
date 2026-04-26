from .base import RuntimeSpec
from ..errors import CoderollError


_RUNTIMES: dict[str, RuntimeSpec] = {
    "python": RuntimeSpec(
        language="python",
        default_image="coderoll-python:3.11",
        default_entry_file="solution.py",
        default_test_file="test_solution.py",
        default_test_command="python -m pytest -q --junitxml=.coderoll-results.xml",
        result_format="junit",
    ),
    "javascript": RuntimeSpec(
        language="javascript",
        default_image="coderoll-node:20",
        default_entry_file="solution.js",
        default_test_file="test_solution.test.js",
        default_test_command="node --test --test-reporter=tap",
        result_format="tap",
    ),
    "typescript": RuntimeSpec(
        language="typescript",
        default_image="coderoll-node-ts:20",
        default_entry_file="solution.ts",
        default_test_file="test_solution.test.ts",
        default_build_command="tsc --noEmit",
        default_test_command="npm test",
        result_format="tap",
    ),
}


def get_runtime(language: str) -> RuntimeSpec:
    key = language.strip().lower()
    try:
        return _RUNTIMES[key]
    except KeyError as exc:
        known = ", ".join(sorted(_RUNTIMES))
        raise CoderollError(f"Unknown runtime language: {language}. Available: {known}") from exc


def list_runtimes() -> list[RuntimeSpec]:
    return [_RUNTIMES[key] for key in sorted(_RUNTIMES)]
