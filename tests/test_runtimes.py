import pytest

from coderoll.cli import _dockerfile_for_runtime
from coderoll.errors import CoderollError
from coderoll.runtimes import get_runtime, list_runtimes


def test_runtime_registry_lists_builtins() -> None:
    languages = [runtime.language for runtime in list_runtimes()]

    assert languages == ["go", "java", "javascript", "python", "rust", "typescript"]


def test_get_runtime_returns_spec() -> None:
    runtime = get_runtime("typescript")

    assert runtime.default_image == "coderoll-node-ts:20"
    assert runtime.default_build_command == "tsc --noEmit"
    assert runtime.result_format == "tap"


def test_get_runtime_returns_go_spec() -> None:
    runtime = get_runtime("go")

    assert runtime.default_image == "coderoll-go:1.26"
    assert runtime.default_entry_file == "solution.go"
    assert runtime.default_test_file == "solution_test.go"
    assert runtime.default_test_command == "GO111MODULE=off go test ./..."
    assert runtime.result_format == "exit_code"


def test_get_runtime_returns_java_spec() -> None:
    runtime = get_runtime("java")

    assert runtime.default_image == "coderoll-java:21"
    assert runtime.default_entry_file == "Solution.java"
    assert runtime.default_test_file == "TestSolution.java"
    assert runtime.default_test_command == "javac *.java && java -ea TestSolution"
    assert runtime.result_format == "exit_code"


def test_get_runtime_returns_rust_spec() -> None:
    runtime = get_runtime("rust")

    assert runtime.default_image == "coderoll-rust:1"
    assert runtime.default_entry_file == "solution.rs"
    assert runtime.default_test_file == "test_solution.rs"
    assert runtime.default_test_command == "rustc --test test_solution.rs -o .coderoll-tests && ./.coderoll-tests"
    assert runtime.result_format == "exit_code"


def test_get_runtime_unknown_language() -> None:
    with pytest.raises(CoderollError, match="Unknown runtime language"):
        get_runtime("ruby")


@pytest.mark.parametrize(
    ("runtime", "expected_from"),
    [
        ("go", "FROM golang:1.26"),
        ("java", "FROM eclipse-temurin:21-jdk"),
        ("python", "FROM python:3.11-slim"),
        ("rust", "FROM rust:1-slim"),
        ("javascript", "FROM node:20-slim"),
        ("typescript", "FROM node:20-slim"),
    ],
)
def test_dockerfile_templates_for_supported_runtimes(runtime: str, expected_from: str) -> None:
    dockerfile = _dockerfile_for_runtime(runtime)

    assert expected_from in dockerfile
    assert "WORKDIR /workspace" in dockerfile
