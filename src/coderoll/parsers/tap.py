import re


def parse_tap_output(text: str) -> dict[str, int | None]:
    result: dict[str, int | None] = {
        "tests_total": None,
        "tests_failed": None,
        "tests_errors": None,
        "tests_skipped": None,
        "tests_passed": None,
    }
    passed_lines = 0
    failed_lines = 0
    skipped_lines = 0
    saw_signal = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        plan = re.match(r"^1\.\.(\d+)\b", line)
        if plan:
            result["tests_total"] = int(plan.group(1))
            saw_signal = True
            continue

        lower = line.lower()
        summary = re.match(r"^#\s*(pass|fail|failed|skipped|skip)\s+(\d+)\b", lower)
        if summary:
            key, value = summary.group(1), int(summary.group(2))
            if key == "pass":
                result["tests_passed"] = value
            elif key in {"fail", "failed"}:
                result["tests_failed"] = value
            else:
                result["tests_skipped"] = value
            saw_signal = True
            continue

        if lower.startswith("not ok "):
            failed_lines += 1
            saw_signal = True
        elif lower.startswith("ok "):
            passed_lines += 1
            if "# skip" in lower:
                skipped_lines += 1
            saw_signal = True

    if not saw_signal:
        return result

    if result["tests_passed"] is None and passed_lines:
        result["tests_passed"] = passed_lines - skipped_lines
    if result["tests_failed"] is None and failed_lines:
        result["tests_failed"] = failed_lines
    if result["tests_skipped"] is None and skipped_lines:
        result["tests_skipped"] = skipped_lines
    if result["tests_errors"] is None:
        result["tests_errors"] = 0

    known_total = result["tests_total"]
    if known_total is None:
        counted = sum(
            value or 0
            for value in (
                result["tests_passed"],
                result["tests_failed"],
                result["tests_skipped"],
                result["tests_errors"],
            )
        )
        if counted:
            result["tests_total"] = counted
    elif result["tests_passed"] is None:
        result["tests_passed"] = max(
            known_total
            - (result["tests_failed"] or 0)
            - (result["tests_errors"] or 0)
            - (result["tests_skipped"] or 0),
            0,
        )

    return result
