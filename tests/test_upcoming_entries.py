"""Every upcoming release-notes and changelog entry starts at a `##`
heading (the TCW 3.0 epic's decision 15), except an entry that carries a major
version's introduction.

`scripts/cut_version.py` writes only the version's `# v{version}` title, and
`combine()` puts any text an entry has before its first `##` above every
heading in the combined file. So only an introduction may have such text:
TCW-75's release-notes entry, whose opening is the 3.0.0 introduction (TCW-75
spec, Design 10.2; criterion 11), and TCW-118's, whose opening is the 4.0.0
introduction (TCW-118 spec, Design 3.3; criterion 7). The heading check runs
over whatever entries exist. The introduction checks read the item's entry
until its version's cut, and the shipped `v{version}.md` after it; before the
cut, the item's two entry files must both exist, so deleting one fails instead
of skipping.
"""

import re
from pathlib import Path

import pytest

from scripts.cut_version import UPCOMING, combine

DOCS = Path(__file__).resolve().parent.parent / "docs"
FOLDERS = ("release-notes", "changelogs")

# The entries allowed text before their first `##` heading: one introduction
# per major version. Every other entry puts everything under a heading (epic
# decision 15), so an introduction is the only leading text and stays first.
class Introduction:
    def __init__(self, version: str, folder: str, guide: str):
        self.version = version
        self.entry = DOCS / "release-notes" / "upcoming" / f"{folder}.md"
        self.changelog_entry = DOCS / "changelogs" / "upcoming" / f"{folder}.md"
        self.guide = guide
        # Written by the version's cut; until then the introduction is in its
        # entry file.
        self.released = DOCS / "release-notes" / f"v{version}.md"

    @property
    def cut(self) -> bool:
        return self.released.exists()


INTRODUCTIONS = (
    Introduction("3.0.0",
                 "2026-10-01-tcw-75-documentation-for-tcw-3-0-readme-guides-and-the-opt-in-git-example",
                 "migration-guide-2.8-to-3.0.0.md"),
    Introduction("4.0.0", "TCW-118-tcw-4-0-release",
                 "migration-guide-3.X-to-4.0.0.md"),
)
INTRODUCTION_ENTRIES = {i.entry for i in INTRODUCTIONS}


def entries():
    return sorted(p for folder in FOLDERS
                  for p in (DOCS / folder / "upcoming").glob("*.md")
                  if p.name != "README.md")


def _leading(text: str) -> str:
    """The text before the first `## ` line."""
    return re.split(r"^## ", text, maxsplit=1, flags=re.M)[0].strip()


@pytest.mark.parametrize("entry", [p for p in entries() if p not in INTRODUCTION_ENTRIES],
                         ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_an_entry_starts_at_a_level_two_heading(entry):
    first = next((line for line in entry.read_text(encoding="utf-8").splitlines()
                  if line.strip()), "")
    assert first.startswith("## "), f"{entry.name} starts with {first!r}"


def test_both_folders_are_read():
    """The glob covers each folder: an entry in either would be checked."""
    assert all((DOCS / folder / "upcoming").is_dir() for folder in FOLDERS)


def _not_cut(introduction):
    """Skips once `introduction`'s version is cut."""
    if introduction.cut:
        pytest.skip(f"folded into v{introduction.version}.md by its cut")


@pytest.mark.parametrize("introduction", INTRODUCTIONS, ids=lambda i: i.version)
def test_the_items_entries_exist_until_the_cut(introduction):
    _not_cut(introduction)
    missing = [p.relative_to(DOCS)
               for p in (introduction.entry, introduction.changelog_entry)
               if not p.exists()]
    assert not missing, (f"entry files missing before the "
                         f"{introduction.version} cut: {missing}")


def _introduction(introduction) -> str:
    """The introduction: the text before the first `##` of the item's
    release-notes entry, or, after the cut, of `v{version}.md` below its
    title."""
    if introduction.cut:
        title, _, body = introduction.released.read_text(encoding="utf-8").partition("\n")
        assert title == f"# v{introduction.version}", title
        return _leading(body)
    return _leading(introduction.entry.read_text(encoding="utf-8"))


@pytest.mark.parametrize("introduction", INTRODUCTIONS, ids=lambda i: i.version)
def test_the_introduction_links_the_migration_guide(introduction):
    leading = _introduction(introduction)
    assert leading, (f"the {introduction.version} introduction has no text "
                     "before its first heading")
    assert f"](../{introduction.guide})" in leading, leading


@pytest.mark.parametrize("introduction", INTRODUCTIONS, ids=lambda i: i.version)
def test_the_cut_puts_the_introduction_first(introduction):
    _not_cut(introduction)
    notes = [p for p in entries() if p.parent.parent.name == "release-notes"]
    combined = combine([p.read_text(encoding="utf-8") for p in notes],
                       UPCOMING["docs/release-notes/upcoming"])
    leading = _introduction(introduction)
    assert combined.startswith(leading), combined[:200]
