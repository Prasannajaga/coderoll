from pathlib import Path

from coderoll.rankers.simple import rank_records
from coderoll.stores.jsonl import JsonlStore


# Results produced by a previous run (for example from 01_run_config.py).
RESULTS_PATH = Path("runs/file_mode_results.jsonl")


def main() -> None:
    # Load all evaluation records from JSONL.
    records = JsonlStore(RESULTS_PATH).read_all()
    # Apply default ranking profile to sort best -> worst.
    ranked = rank_records(records)

    # Print a readable leaderboard.
    for index, record in enumerate(ranked, start=1):
        print(
            f"{index}. candidate_id={record.candidate_id} "
            f"score={record.score:.3f} "
            f"passed={record.passed} "
            f"duration_ms={record.duration_ms}"
        )


if __name__ == "__main__":
    main()
