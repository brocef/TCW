"""Every upcoming release-notes and changelog entry starts at a `##`
heading (the TCW 3.0 epic's decision 15), except the one entry that carries
the 3.0.0 introduction.

`scripts/cut_version.py` writes only the version's `# v{version}` title, and
`combine()` puts any text an entry has before its first `##` above every
heading in the combined file. So exactly one entry may have such text: TCW-75's
release-notes entry, whose opening is the 3.0.0 introduction (TCW-75 spec,
Design 10.2; criterion 11). Checked over whatever entries exist, so the checks
still pass once a cut has folded them away.
"""

import re
from pathlib import Path

import pytest

from scripts.cut_version import UPCOMING, combine

DOCS = Path(__file__).resolve().parent.parent / "docs"
FOLDERS = ("release-notes", "changelogs")

# The one entry allowed text before its first `##` heading: the 3.0.0
# introduction. Every other entry puts everything under a heading (epic
# decision 15), so this introduction is the only leading text and stays first.
INTRODUCTION = (DOCS / "release-notes" / "upcoming" /
                "2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example.md")
MIGRATION_GUIDE = "migration-guide-2.8-to-3.0.0.md"


def entries():
    return sorted(p for folder in FOLDERS
                  for p in (DOCS / folder / "upcoming").glob("*.md")
                  if p.name != "README.md")


def _leading(text: str) -> str:
    """The text before the first `## ` line."""
    return re.split(r"^## ", text, maxsplit=1, flags=re.M)[0].strip()


@pytest.mark.parametrize("entry", [p for p in entries() if p != INTRODUCTION],
                         ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_an_entry_starts_at_a_level_two_heading(entry):
    first = next((line for line in entry.read_text(encoding="utf-8").splitlines()
                  if line.strip()), "")
    assert first.startswith("## "), f"{entry.name} starts with {first!r}"


def test_both_folders_are_read():
    """The glob covers each folder: an entry in either would be checked."""
    assert all((DOCS / folder / "upcoming").is_dir() for folder in FOLDERS)


@pytest.mark.skipif(not INTRODUCTION.exists(), reason="folded away by the 3.0.0 cut")
def test_the_introduction_links_the_migration_guide():
    leading = _leading(INTRODUCTION.read_text(encoding="utf-8"))
    assert leading, f"{INTRODUCTION.name} has no text before its first heading"
    assert f"](../{MIGRATION_GUIDE})" in leading, leading


@pytest.mark.skipif(not INTRODUCTION.exists(), reason="folded away by the 3.0.0 cut")
def test_the_cut_puts_the_introduction_first():
    notes = [p for p in entries() if p.parent.parent.name == "release-notes"]
    combined = combine([p.read_text(encoding="utf-8") for p in notes],
                       UPCOMING["docs/release-notes/upcoming"])
    leading = _leading(INTRODUCTION.read_text(encoding="utf-8"))
    assert combined.startswith(leading), combined[:200]
