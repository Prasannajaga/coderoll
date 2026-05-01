from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import textwrap

from .config import EvalCommandConfig, SandboxConfig
from .errors import CoderollError
from .runtimes import get_runtime
from .sandboxes.docker_cli import DockerSandbox


@dataclass
class SimpleExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


def execute_simple(
    *,
    sandbox: SandboxConfig,
    language: str = "python",
    code: str | None = None,
    file: str | Path | None = None,
    command: str | None = None,
    filename: str | None = None,
) -> SimpleExecutionResult:
    if (code is None and file is None) or (code is not None and file is not None):
        raise CoderollError("Provide exactly one of `code` or `file`.")

    runtime = get_runtime(language)
    entry_name = filename or runtime.default_entry_file
    run_command = command or _default_run_command(language=language, entry_name=entry_name)

    workspace = Path(tempfile.mkdtemp(prefix="coderoll_simple_exec_"))
    try:
        entry_path = workspace / entry_name
        entry_path.parent.mkdir(parents=True, exist_ok=True)

        if code is not None:
            prepared_code = _prepare_inline_code(language=language, code=code)
            entry_path.write_text(prepared_code, encoding="utf-8")
        else:
            source_path = Path(file) if file is not None else None
            if source_path is None or not source_path.exists() or not source_path.is_file():
                raise CoderollError(f"Input file does not exist or is not a file: {file}")
            shutil.copy2(source_path, entry_path)

        docker = DockerSandbox()
        exec_result = docker.run_workspace(
            workspace_path=workspace,
            setup_commands=[],
            eval_commands=[
                EvalCommandConfig(
                    name="run_code",
                    command=run_command,
                    result_format="exit_code",
                )
            ],
            sandbox_config=sandbox,
            task_id="simple_exec",
            candidate_id="inline" if code is not None else str(Path(file).name),
            stop_on_first_failure=True,
            image=sandbox.image or runtime.default_image,
            language=language,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    first_eval = next((item for item in exec_result.command_results if item.phase == "eval"), None)
    stdout = first_eval.stdout if first_eval is not None else exec_result.test_stdout or exec_result.stdout
    stderr = first_eval.stderr if first_eval is not None else exec_result.test_stderr or exec_result.stderr

    return SimpleExecutionResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exec_result.exit_code,
        duration_ms=exec_result.duration_ms,
        timed_out=exec_result.timed_out,
        error=exec_result.error,
    )


def _default_run_command(language: str, entry_name: str) -> str:
    key = language.strip().lower()
    if key == "python":
        return f"python {entry_name}"
    if key == "javascript":
        return f"node {entry_name}"
    if key == "typescript":
        return f"npx ts-node {entry_name}"
    if key == "go":
        return f"go run {entry_name}"
    if key == "rust":
        return f"rustc {entry_name} -o .coderoll-bin && ./.coderoll-bin"
    if key == "java":
        class_name = Path(entry_name).stem
        return f"javac {entry_name} && java {class_name}"
    raise CoderollError(f"Unsupported language for default execute command: {language}")


def _prepare_inline_code(*, language: str, code: str) -> str:
    # Keep behavior stable for non-indented snippets while fixing common triple-quoted indentation.
    normalized = textwrap.dedent(code).lstrip("\n")
    if not normalized.strip():
        return normalized

    key = language.strip().lower()
    if key == "python":
        # Validate the normalized Python source. If parsing fails, keep original input unchanged
        # so we do not regress existing callers that intentionally rely on exact formatting.
        try:
            ast.parse(normalized)
            return normalized
        except SyntaxError:
            return code

    return normalized
