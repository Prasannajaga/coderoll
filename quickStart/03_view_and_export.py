from pathlib import Path

from coderoll.exporters import export_preferences, export_rewards, export_sft
from coderoll.stores.jsonl import JsonlStore
from coderoll.viewer import write_viewer


RESULTS_PATH = Path("runs/file_mode_results.jsonl")


def main() -> None:
    records = JsonlStore(RESULTS_PATH).read_all()

    viewer_path = write_viewer(
        records,
        "runs/file_mode.sdk.viewer.html",
        title="coderoll SDK quick start",
    )
    rewards_count = export_rewards(
        records,
        "datasets/file_mode_rewards.sdk.jsonl",
        include_metadata=True,
    )
    sft_count = export_sft(records, "datasets/file_mode_sft.sdk.jsonl")
    preference_count = export_preferences(
        records,
        "datasets/file_mode_preferences.sdk.jsonl",
    )

    print("viewer:", viewer_path)
    print("rewards rows:", rewards_count)
    print("sft rows:", sft_count)
    print("preference rows:", preference_count)


if __name__ == "__main__":
    main()
