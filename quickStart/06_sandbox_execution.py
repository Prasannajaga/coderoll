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
        code="""
        import random

        # Generate a random integer between 1 and 100
        num = random.randint(1, 100)
        print(f"Random Number: {num}")

        # Pick a random item from a list
        choices = ['Apple', 'Banana', 'Cherry', 'Dragonfruit']
        pick = random.choice(choices)
        print(f"I chose: {pick}")

        # Shuffle a list in place
        deck = [1, 2, 3, 4, 5]
        random.shuffle(deck)
        print(f"Shuffled deck: {deck}")  
        """,
    )

    print("Result: \n" , inline_result.stdout , inline_result.stderr)

    # Case 2: execute a real source file (copied to sandbox workspace internally).
    sample_file = Path("runs/quickstart_simple_exec.py")
    sample_file.parent.mkdir(parents=True, exist_ok=True)
    sample_file.write_text("print('hello from file input')\n", encoding="utf-8")

    file_result = execute_simple(
        sandbox=sandbox,
        language="python",
        file=sample_file,
    )
    print("Result: \n" , file_result.stdout)

if __name__ == "__main__":
    main()
