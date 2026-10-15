"""Every upcoming release-notes and changelog entry starts at a `##`
heading (the TCW 3.0 epic's decision 15), except the one entry that carries
the 3.0.0 introduction.

`scripts/cut_version.py` writes only the version's `# v{version}` title, and
`combine()` puts any text an entry has before its first `##` above every
heading in the combined file. So exactly one entry may have such text: TCW-75's
release-notes entry, whose opening is the 3.0.0 introduction (TCW-75 spec,
Design 10.2; criterion 11). The heading check runs over whatever entries
exist. The introduction checks read this item's entry until the 3.0.0 cut, and
the shipped `v3.0.0.md` after it; before the cut, this item's two entry files
must both exist, so deleting one fails instead of skipping.
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
CHANGELOG_ENTRY = (DOCS / "changelogs" / "upcoming" / INTRODUCTION.name)
MIGRATION_GUIDE = "migration-guide-2.8-to-3.0.0.md"
# Written by the 3.0.0 cut; until then the introduction is in its entry file.
RELEASED = DOCS / "release-notes" / "v3.0.0.md"
CUT = RELEASED.exists()


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


@pytest.mark.skipif(CUT, reason="folded into v3.0.0.md by the 3.0.0 cut")
def test_this_items_entries_exist_until_the_cut():
    missing = [p.relative_to(DOCS) for p in (INTRODUCTION, CHANGELOG_ENTRY)
               if not p.exists()]
    assert not missing, f"entry files missing before the 3.0.0 cut: {missing}"


def _introduction() -> str:
    """The introduction: the text before the first `##` of this item's
    release-notes entry, or, after the cut, of `v3.0.0.md` below its title."""
    if CUT:
        title, _, body = RELEASED.read_text(encoding="utf-8").partition("\n")
        assert title == "# v3.0.0", title
        return _leading(body)
    return _leading(INTRODUCTION.read_text(encoding="utf-8"))


def test_the_introduction_links_the_migration_guide():
    leading = _introduction()
    assert leading, "the 3.0.0 introduction has no text before its first heading"
    assert f"](../{MIGRATION_GUIDE})" in leading, leading


@pytest.mark.skipif(CUT, reason="folded into v3.0.0.md by the 3.0.0 cut")
def test_the_cut_puts_the_introduction_first():
    notes = [p for p in entries() if p.parent.parent.name == "release-notes"]
    combined = combine([p.read_text(encoding="utf-8") for p in notes],
                       UPCOMING["docs/release-notes/upcoming"])
    leading = _introduction()
    assert combined.startswith(leading), combined[:200]
