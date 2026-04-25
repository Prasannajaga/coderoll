import pytest

from coderoll.errors import CoderollError
from coderoll.runtimes import get_runtime, list_runtimes


def test_runtime_registry_lists_builtins() -> None:
    languages = [runtime.language for runtime in list_runtimes()]

    assert languages == ["javascript", "python", "typescript"]


def test_get_runtime_returns_spec() -> None:
    runtime = get_runtime("typescript")

    assert runtime.default_image == "coderoll-node-ts:20"
    assert runtime.default_build_command == "npx tsc --noEmit"
    assert runtime.result_format == "tap"


def test_get_runtime_unknown_language() -> None:
    with pytest.raises(CoderollError, match="Unknown runtime language"):
        get_runtime("ruby")
