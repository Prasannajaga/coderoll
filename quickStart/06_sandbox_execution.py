from pathlib import Path

from coderoll.simple import SandboxConfig, execute_simple


def main() -> None:
    # Only sandbox limits/config are required for simple execution.
    sandbox = SandboxConfig(
        image="coderoll-python:3.11",
        timeout=10,
        memory="256m",
        cpus="1",
        pids_limit=128,
        network=False,
    )

    # Case 1: execute inline code string (written to temp file internally).
    inline_result = execute_simple(
        sandbox=sandbox,
        language="python",
        code="print('hello from inline code')",
    )
    print("inline stdout:", inline_result.stdout.strip())

    # Case 2: execute a real source file (copied to sandbox workspace internally).
    sample_file = Path("runs/quickstart_simple_exec.py")
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text("print('hello from file input')\n", encoding="utf-8")

    file_result = execute_simple(
        sandbox=sandbox,
        language="python",
        file=sample_file,
    )
    print("file stdout:", file_result.stdout.strip())
    print("file exit_code:", file_result.exit_code)


if __name__ == "__main__":
    main()
