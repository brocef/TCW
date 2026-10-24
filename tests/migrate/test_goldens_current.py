"""Each golden was recorded from the fixture as it is built today (TCW-116
plan, Decided 3).

`tests/migrate/record_3x_listings.py` records TCW 3.0.2's answers about each
fixture into `tests/migrate/golden/<fixture>.json`, with the fixture's digest.
A fixture changed since then would be compared, silently, against answers
about another fixture; this says so instead, and names the script.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.migrate.fixtures import FIXTURES, build_fixture, fixture_digest_of

GOLDEN = Path(__file__).resolve().parent / "golden"


def golden(name: str) -> dict:
    return json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


def stale(name: str, tmp_path: Path) -> str | None:
    """Why `name`'s golden does not describe the fixture built today, or None."""
    root = build_fixture(name, tmp_path / name, config_home=tmp_path / f"{name}-config")
    if golden(name)["fixture-digest"] != fixture_digest_of(name, root,
                                                           tmp_path / f"{name}-config"):
        return (f"golden/{name}.json was recorded from another fixture; run "
                f"tests/migrate/record_3x_listings.py")
    return None


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_each_golden_describes_the_fixture_built_today(name, tmp_path):
    assert stale(name, tmp_path) is None


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_no_golden_holds_a_temporary_path(name):
    text = (GOLDEN / f"{name}.json").read_text(encoding="utf-8")
    assert "/tmp" not in text and "/var/folders" not in text and "tcw116-" not in text


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_each_golden_is_3_0_2s(name):
    assert golden(name)["tcw-version"] == "tcw 3.0.2"


def test_a_changed_fixture_is_noticed(tmp_path, monkeypatch):
    from tests.migrate import fixtures
    changed = dict(fixtures._CAPABILITIES)
    changed["cli/x/meta.yaml"] = changed["cli/x/meta.yaml"].replace("Do X", "Do x")
    monkeypatch.setattr(fixtures, "_CAPABILITIES", changed)
    assert stale("f-single", tmp_path) == (
        "golden/f-single.json was recorded from another fixture; run "
        "tests/migrate/record_3x_listings.py")
