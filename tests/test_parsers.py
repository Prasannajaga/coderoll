from pathlib import Path

from coderoll.parsers import parse_junit_xml, parse_tap_output


def test_parse_junit_xml(tmp_path: Path) -> None:
    path = tmp_path / "results.xml"
    path.write_text(
        '<testsuite tests="3" failures="1" errors="0" skipped="1">'
        '<testcase name="a"/>'
        '<testcase name="b"><failure /></testcase>'
        '<testcase name="c"><skipped /></testcase>'
        "</testsuite>",
        encoding="utf-8",
    )

    result = parse_junit_xml(path)

    assert result == {
        "tests_total": 3,
        "tests_failed": 1,
        "tests_errors": 0,
        "tests_skipped": 1,
        "tests_passed": 1,
    }


def test_parse_tap_output() -> None:
    result = parse_tap_output(
        "TAP version 13\n"
        "ok 1 - adds one\n"
        "not ok 2 - fails\n"
        "ok 3 - skipped # SKIP reason\n"
        "1..3\n"
        "# pass 1\n"
        "# fail 1\n"
    )

    assert result["tests_total"] == 3
    assert result["tests_passed"] == 1
    assert result["tests_failed"] == 1
    assert result["tests_errors"] == 0
    assert result["tests_skipped"] == 1
