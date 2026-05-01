from .base import RuntimeSpec
from ..errors import CoderollError


_RUNTIMES: dict[str, RuntimeSpec] = {
    "go": RuntimeSpec(
        language="go",
        default_image="coderoll-go:1.26",
        default_entry_file="solution.go",
        default_test_file="solution_test.go",
        default_test_command="GO111MODULE=off go test ./...",
        result_format="exit_code",
    ),
    "java": RuntimeSpec(
        language="java",
        default_image="coderoll-java:21",
        default_entry_file="Solution.java",
        default_test_file="TestSolution.java",
        default_test_command="javac *.java && java -ea TestSolution",
        result_format="exit_code",
    ),
    "python": RuntimeSpec(
        language="python",
        default_image="coderoll-python:3.11",
        default_entry_file="solution.py",
        default_test_file="test_solution.py",
        default_test_command="python -m pytest -q --junitxml=.coderoll-results.xml",
        result_format="junit",
    ),
    "rust": RuntimeSpec(
        language="rust",
        default_image="coderoll-rust:1",
        default_entry_file="solution.rs",
        default_test_file="test_solution.rs",
        default_test_command="rustc --test test_solution.rs -o .coderoll-tests && ./.coderoll-tests",
        result_format="exit_code",
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
