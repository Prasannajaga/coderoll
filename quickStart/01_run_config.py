from pathlib import Path

from coderoll.config import load_config
from coderoll.runner import run_from_config


CONFIG_PATH = Path("examples/file_mode/experiment.yaml")


def main() -> None:
    config = load_config(CONFIG_PATH)
    results = run_from_config(config)

    print("summary:", results.summary())
    best = results.best()
    if best is not None:
        print(
            "best:",
            {
                "candidate_id": best.candidate_id,
                "score": best.score,
                "passed": best.passed,
            },
        )
    print("output:", config.output_path)


if __name__ == "__main__":
    main()
