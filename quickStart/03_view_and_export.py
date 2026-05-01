from pathlib import Path

from coderoll.exporters import export_preferences, export_rewards, export_sft
from coderoll.stores.jsonl import JsonlStore
from coderoll.viewer import write_viewer


# Results produced by a previous run (for example from 01_run_config.py).
RESULTS_PATH = Path("runs/file_mode_results.jsonl")


def main() -> None:
    # Load all evaluation records from JSONL.
    records = JsonlStore(RESULTS_PATH).read_all()

    # Build an HTML viewer for quick manual inspection in a browser.
    viewer_path = write_viewer(
        records,
        "runs/file_mode.sdk.viewer.html",
        title="coderoll SDK quick start",
    )
    # Export rewards-style dataset rows (prompt/completion/reward).
    rewards_count = export_rewards(
        records,
        "datasets/file_mode_rewards.sdk.jsonl",
        include_metadata=True,
    )
    # Export supervised fine-tuning style examples.
    sft_count = export_sft(records, "datasets/file_mode_sft.sdk.jsonl")
    # Export pairwise preference examples for preference training.
    preference_count = export_preferences(
        records,
        "datasets/file_mode_preferences.sdk.jsonl",
    )

    # Print generated artifact paths and row counts.
    print("viewer:", viewer_path)
    print("rewards rows:", rewards_count)
    print("sft rows:", sft_count)
    print("preference rows:", preference_count)


if __name__ == "__main__":
    main()
