from pathlib import Path
import xml.etree.ElementTree as ET


def parse_junit_xml(path: Path) -> dict[str, int]:
    empty = {
        "tests_total": 0,
        "tests_failed": 0,
        "tests_errors": 0,
        "tests_skipped": 0,
        "tests_passed": 0,
    }
    if not path.exists():
        return dict(empty)

    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return dict(empty)

    totals = {
        "tests_total": 0,
        "tests_failed": 0,
        "tests_errors": 0,
        "tests_skipped": 0,
    }

    suites = [root] if _strip_ns(root.tag) == "testsuite" else [
        node for node in root.iter() if _strip_ns(node.tag) == "testsuite"
    ]
    if suites:
        for suite in suites:
            totals["tests_total"] += _attr_int(suite, "tests")
            totals["tests_failed"] += _attr_int(suite, "failures")
            totals["tests_errors"] += _attr_int(suite, "errors")
            totals["tests_skipped"] += _attr_int(suite, "skipped")
    else:
        cases = [node for node in root.iter() if _strip_ns(node.tag) == "testcase"]
        totals["tests_total"] = len(cases)
        for case in cases:
            if any(_strip_ns(child.tag) == "failure" for child in case):
                totals["tests_failed"] += 1
            if any(_strip_ns(child.tag) == "error" for child in case):
                totals["tests_errors"] += 1
            if any(_strip_ns(child.tag) == "skipped" for child in case):
                totals["tests_skipped"] += 1

    totals["tests_passed"] = max(
        totals["tests_total"]
        - totals["tests_failed"]
        - totals["tests_errors"]
        - totals["tests_skipped"],
        0,
    )
    return totals


def _attr_int(node: ET.Element, name: str) -> int:
    try:
        return int(node.attrib.get(name, "0"))
    except ValueError:
        return 0


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
