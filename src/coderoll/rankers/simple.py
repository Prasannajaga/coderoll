from ..result import RunRecord


def rank_records(records: list[RunRecord]) -> list[RunRecord]:
    return sorted(
        records,
        key=lambda record: (
            -record.score,
            0 if record.passed else 1,
            record.duration_ms,
            record.candidate_id,
        ),
    )
