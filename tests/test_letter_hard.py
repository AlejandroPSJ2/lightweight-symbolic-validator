"""Tests for the hard letter-count benchmark profile."""

from benchmark.letters.generate import generate_hard_cases, write_datasets


def test_generate_hard_cases_has_30():
    cases = generate_hard_cases()
    assert len(cases) == 30
    assert cases[0]["word"] == "strawberry"
    assert cases[0]["target"] == "r"
    assert cases[0]["expected_count"] == 3


def test_write_hard_datasets(tmp_path):
    path = write_datasets(tmp_path, profile="hard")
    assert (path / "cases.json").exists()
    assert (path / "meta.json").exists()
    cases = __import__("json").loads((path / "cases.json").read_text(encoding="utf-8"))
    assert any("note" in case and "errónea" in case["note"] for case in cases)
