from pathlib import Path

from app.slugify import slugify


def test_candidate_dependency_command_ran():
    assert Path(".candidate_dep_ready").read_text(encoding="utf-8") == "ok"


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  Multi   Space  ") == "multi-space"
