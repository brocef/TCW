"""Every upcoming release-notes and changelog entry starts at a `##`
heading (the TCW 3.0 epic's decision 15).

`scripts/cut_version.py` writes the version's own introduction; an entry that
opened with text of its own would land above every heading in the combined
file. Checked over whatever entries exist, so it still passes once a cut has
folded them away: no test names an entry, because the cut deletes them.
"""

from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parent.parent / "docs"
FOLDERS = ("release-notes", "changelogs")


def entries():
    return sorted(p for folder in FOLDERS
                  for p in (DOCS / folder / "upcoming").glob("*.md")
                  if p.name != "README.md")


@pytest.mark.parametrize("entry", entries(),
                         ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_an_entry_starts_at_a_level_two_heading(entry):
    first = next((line for line in entry.read_text(encoding="utf-8").splitlines()
                  if line.strip()), "")
    assert first.startswith("## "), f"{entry.name} starts with {first!r}"


def test_both_folders_are_read():
    """The glob covers each folder: an entry in either would be checked."""
    assert all((DOCS / folder / "upcoming").is_dir() for folder in FOLDERS)
