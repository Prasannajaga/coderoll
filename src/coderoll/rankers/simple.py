from typing import Any, Literal, TypeAlias

from ..result import RunRecord

RankProfile: TypeAlias = Literal["default", "strict", "debug"]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
        return default
    return bool(value)


def phase_rank(phase: str | None) -> int:
    normalized = _normalize_phase(phase)
    mapping = {
        "complete": 0,
        "eval": 1,
        "setup": 2,
        "timeout": 3,
        "infra": 4,
    }
    return mapping.get(normalized, 5)


def debug_phase_rank(phase: str | None) -> int:
    normalized = _normalize_phase(phase)
    mapping = {
        "infra": 0,
        "timeout": 1,
        "setup": 2,
        "eval": 3,
        "complete": 4,
    }
    return mapping.get(normalized, 5)


def has_structured_tests(record: RunRecord) -> bool:
    if getattr(record, "tests_total", None) is not None:
        return True
    return any(
        getattr(record, field, None) is not None
        for field in ("tests_passed", "tests_failed", "tests_errors", "tests_skipped")
    )


def test_pass_ratio(record: RunRecord) -> float:
    tests_total = max(safe_int(getattr(record, "tests_total", 0), default=0), 0)
    if tests_total > 0:
        tests_passed = max(safe_int(getattr(record, "tests_passed", 0), default=0), 0)
        ratio = tests_passed / tests_total
    else:
        ratio = 1.0 if safe_bool(getattr(record, "passed", False), default=False) else 0.0
    return min(max(ratio, 0.0), 1.0)


test_pass_ratio.__test__ = False


def candidate_size(record: RunRecord) -> int:
    files = getattr(record, "files", None)
    if isinstance(files, dict):
        return sum(len(str(content)) for content in files.values())
    code = getattr(record, "code", None)
    if code is None:
        return 0
    return len(str(code))


def default_rank_key(record: RunRecord) -> tuple:
    return (
        0 if safe_bool(getattr(record, "passed", False), default=False) else 1,
        -safe_float(getattr(record, "score", 0.0), default=0.0),
        phase_rank(getattr(record, "phase", None)),
        0 if safe_bool(getattr(record, "setup_passed", False), default=False) else 1,
        0 if not safe_bool(getattr(record, "timed_out", False), default=False) else 1,
        -test_pass_ratio(record),
        max(safe_int(getattr(record, "tests_failed", 0), default=0), 0),
        max(safe_int(getattr(record, "tests_errors", 0), default=0), 0),
        max(safe_int(getattr(record, "tests_skipped", 0), default=0), 0),
        max(safe_int(getattr(record, "duration_ms", 0), default=0), 0),
        candidate_size(record),
        str(getattr(record, "candidate_id", "")),
    )


def strict_rank_key(record: RunRecord) -> tuple:
    tests_failed = max(safe_int(getattr(record, "tests_failed", 0), default=0), 0)
    tests_errors = max(safe_int(getattr(record, "tests_errors", 0), default=0), 0)
    tests_skipped = max(safe_int(getattr(record, "tests_skipped", 0), default=0), 0)
    return (
        0 if safe_bool(getattr(record, "passed", False), default=False) else 1,
        0 if not safe_bool(getattr(record, "timed_out", False), default=False) else 1,
        0 if safe_bool(getattr(record, "setup_passed", False), default=False) else 1,
        0 if tests_failed == 0 else 1,
        0 if tests_errors == 0 else 1,
        0 if tests_skipped == 0 else 1,
        -safe_float(getattr(record, "score", 0.0), default=0.0),
        max(safe_int(getattr(record, "duration_ms", 0), default=0), 0),
        candidate_size(record),
        str(getattr(record, "candidate_id", "")),
    )


def debug_rank_key(record: RunRecord) -> tuple:
    return (
        _debug_failure_rank(record),
        debug_phase_rank(getattr(record, "phase", None)),
        safe_float(getattr(record, "score", 0.0), default=0.0),
        -max(safe_int(getattr(record, "duration_ms", 0), default=0), 0),
        str(getattr(record, "candidate_id", "")),
    )


def rank_records(records: list[RunRecord], profile: RankProfile = "default") -> list[RunRecord]:
    if profile == "default":
        key_fn = default_rank_key
    elif profile == "strict":
        key_fn = strict_rank_key
    elif profile == "debug":
        key_fn = debug_rank_key
    else:
        raise ValueError(
            f"Unknown ranking profile '{profile}'. Allowed profiles: default, strict, debug"
        )
    return sorted(records, key=key_fn)


def explain_rank(record: RunRecord) -> dict[str, Any]:
    phase_value = getattr(record, "phase", None)
    passed = safe_bool(getattr(record, "passed", False), default=False)
    timed_out = safe_bool(getattr(record, "timed_out", False), default=False)
    raw_setup_passed = getattr(record, "setup_passed", None)
    setup_passed = safe_bool(raw_setup_passed, default=False)
    tests_total = max(safe_int(getattr(record, "tests_total", 0), default=0), 0)
    tests_passed = max(safe_int(getattr(record, "tests_passed", 0), default=0), 0)

    reason = "failed during eval"
    normalized_phase = _normalize_phase(phase_value)
    if normalized_phase == "infra":
        reason = "infra failure"
    elif timed_out or normalized_phase == "timeout":
        reason = "timed out"
    elif raw_setup_passed is False or normalized_phase == "setup":
        reason = "setup failed"
    elif passed:
        reason = "fully passed, no timeout"
    elif tests_total > 0 and 0 < tests_passed < tests_total:
        reason = f"partial pass: {tests_passed}/{tests_total} tests passed"

    return {
        "candidate_id": str(getattr(record, "candidate_id", "")),
        "passed": passed,
        "score": safe_float(getattr(record, "score", 0.0), default=0.0),
        "phase": phase_value,
        "setup_passed": setup_passed,
        "timed_out": timed_out,
        "tests_total": tests_total,
        "tests_passed": tests_passed,
        "tests_failed": max(safe_int(getattr(record, "tests_failed", 0), default=0), 0),
        "tests_errors": max(safe_int(getattr(record, "tests_errors", 0), default=0), 0),
        "tests_skipped": max(safe_int(getattr(record, "tests_skipped", 0), default=0), 0),
        "test_pass_ratio": test_pass_ratio(record),
        "duration_ms": max(safe_int(getattr(record, "duration_ms", 0), default=0), 0),
        "candidate_size": candidate_size(record),
        "reason": reason,
    }


def _normalize_phase(phase: str | None) -> str:
    if phase is None:
        return "unknown"
    normalized = str(phase).strip().lower()
    return normalized if normalized else "unknown"


def _debug_failure_rank(record: RunRecord) -> int:
    phase = _normalize_phase(getattr(record, "phase", None))
    if phase == "infra":
        return 0
    if safe_bool(getattr(record, "timed_out", False), default=False) or phase == "timeout":
        return 1
    setup_passed = getattr(record, "setup_passed", None)
    if setup_passed is False or phase == "setup":
        return 2
    if not safe_bool(getattr(record, "passed", False), default=False) or phase == "eval":
        return 3
    if phase == "complete":
        return 4
    return debug_phase_rank(getattr(record, "phase", None))
