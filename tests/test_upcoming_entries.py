"""Every upcoming release-notes entry starts at a `##` heading (the TCW 3.0
epic's decision 15).

`scripts/cut_version.py` writes the version's own introduction; an entry that
opened with text of its own would land above every heading in the combined
file. Checked over whatever entries exist, so it still passes once a cut has
folded them away.
"""

from pathlib import Path

import pytest

UPCOMING = Path(__file__).resolve().parent.parent / "docs" / "release-notes" / "upcoming"


def entries():
    return sorted(p for p in UPCOMING.glob("*.md") if p.name != "README.md")


@pytest.mark.parametrize("entry", entries(), ids=lambda p: p.name)
def test_an_entry_starts_at_a_level_two_heading(entry):
    first = next((line for line in entry.read_text(encoding="utf-8").splitlines()
                  if line.strip()), "")
    assert first.startswith("## "), f"{entry.name} starts with {first!r}"
