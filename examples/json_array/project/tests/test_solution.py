from solution import normalize_name


def test_normalize_name():
    assert normalize_name("  Ada ") == "ada"
    assert normalize_name("GRACE") == "grace"
