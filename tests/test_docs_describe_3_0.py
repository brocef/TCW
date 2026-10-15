"""The documents TCW-75 owns describe TCW 3.0, and nothing else (TCW-75 spec,
acceptance criteria 2, 3 and 4).

"Owned documents" are the README, every guide but `web-viewer.md`, the three
lifecycle documents, the `configure` skill, and the section of `AGENTS.md`
headed `### Working in a git worktree` (`CLAUDE.md` is a symbolic link to
`AGENTS.md`, so it is not read again). Three scans read them:

- the 2.x vocabulary scan (criterion 2), with the table TCW-74 wrote in
  `tests/doc_vocabulary.py`, shared with its own scan of the skills;
- the link check (criterion 3): every relative Markdown link points at a file
  that exists, and an `#anchor` into an owned document at a heading in it;
- the allowance-name check (criterion 4): no owned document names an entry of
  the temporary allowance in `tests/doc_allowance.py`, read with the same
  helpers TCW-74's scans use, so the two cannot read a document differently.

The scans grow one document at a time: `REWRITTEN` lists the owned documents
rewritten so far, and each document joins it in the commit that rewrites it,
so a document is guarded from then on and the suite passes at every commit.
"""

import re
from pathlib import Path

import pytest

from tests.doc_allowance import (REFUSED_KEYS, REFUSED_VALUES, REMOVED_COMMANDS,
                                  REMOVED_FLAGS, REMOVED_FORMS)
from tests.doc_vocabulary import PATTERNS, scan
from tests.test_shipped_text import _flag_named, _names

REPO = Path(__file__).resolve().parent.parent

AGENTS = "AGENTS.md"
AGENTS_HEADING = "### Working in a git worktree"

# The owned documents rewritten so far, by path from the repository root.
# `AGENTS.md` stands for its worktree section only (`agents_worktree_section`).
REWRITTEN: tuple[str, ...] = (
    AGENTS,
    "docs/lifecycle/abstraction.md",
    "docs/lifecycle/harness.md",
    "docs/lifecycle/implementation.md",
    "skills/configure/SKILL.md",
    "skills/configure/references/docs-sync.md",
    "skills/configure/references/jira.md",
    "skills/configure/references/personal.md",
    "skills/configure/references/projects.md",
    "skills/configure/references/stores.md",
    "skills/configure/references/work.md",
)

# Link targets that do not exist yet, each with the item that writes it.
# TCW-76 writes the migration guide and removes this entry when it does.
PENDING_TARGETS = ("docs/migration-guide-2.8-to-3.0.0.md",)



def agents_worktree_section(text: str | None = None) -> str:
    """The owned part of `AGENTS.md`: from the line `### Working in a git
    worktree` up to the next line starting `## `. Fails when the heading is
    missing, so a renamed heading cannot make the scans read nothing."""
    if text is None:
        text = (REPO / AGENTS).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip() == AGENTS_HEADING]
    assert starts, f"{AGENTS} has no line {AGENTS_HEADING!r}"
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## ")), len(lines))
    return "".join(lines[start:end])


def owned_text(rel: str) -> str:
    """What the scans read for one entry of `REWRITTEN`."""
    if rel == AGENTS:
        return agents_worktree_section()
    return (REPO / rel).read_text(encoding="utf-8")


def owned_paths() -> set[str]:
    """Every owned document's path, by glob, whether rewritten yet or not:
    the documents whose headings an `#anchor` link is checked against."""
    found = {"README.md", AGENTS,
             "docs/lifecycle/abstraction.md", "docs/lifecycle/implementation.md",
             "docs/lifecycle/harness.md", "skills/configure/SKILL.md"}
    found |= {p.relative_to(REPO).as_posix() for p in (REPO / "docs/guide").glob("*.md")
              if p.name != "web-viewer.md"}
    found |= {p.relative_to(REPO).as_posix()
              for p in (REPO / "skills/configure/references").glob("*.md")}
    return found


# ── criterion 2: no 2.x vocabulary ────────────────────────────────────────────


def vocabulary_problems(rel: str, text: str) -> list[str]:
    """Every match of criterion 2's table, one line each. The table alone:
    `builtin: true` is not in it, since `tcw config show` prints it."""
    lines = text.splitlines()
    return [f"{rel}:{h.line}: {h.text!r} ({h.reason}): {lines[h.line - 1].strip()}"
            for h in scan(text, PATTERNS)]


@pytest.mark.parametrize("rel", REWRITTEN)
def test_no_owned_document_uses_2x_vocabulary(rel):
    problems = vocabulary_problems(rel, owned_text(rel))
    assert not problems, "2.x vocabulary:\n  " + "\n  ".join(problems)


def test_the_vocabulary_scan_sees_a_removed_command():
    assert vocabulary_problems("x.md", "Run `tcw work start <slug>` first.")


def test_the_vocabulary_scan_passes_builtin_true():
    assert not vocabulary_problems("x.md", "- builtin: true  # built-in")


def test_inserting_a_removed_command_into_an_owned_document_fails(tmp_path):
    """Criterion 2's own mutation: a real owned document, copied, with
    `tcw work start` inserted, is reported at the inserted line."""
    source = REPO / "docs/guide/work.md"
    lines = source.read_text(encoding="utf-8").splitlines()
    at = len(lines) // 2
    lines.insert(at, "Then run `tcw work start <slug>`.")
    copy = tmp_path / "work.md"
    copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = vocabulary_problems("work.md", copy.read_text(encoding="utf-8"))
    assert any(p.startswith(f"work.md:{at + 1}: 'tcw work start'") for p in problems), \
        problems


# ── criterion 3: links resolve ────────────────────────────────────────────────

FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
LINK = re.compile(r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SKIPPED_SCHEMES = ("http:", "https:", "mailto:", "tcw:")
HEADING = re.compile(r"^#{1,6}[ \t]+(.*?)[ \t]*#*[ \t]*$")


def _outside_fences(text: str) -> str:
    """The text with every fenced code block blanked, line count kept."""
    return FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def links(text: str) -> list[tuple[int, str]]:
    """Every inline Markdown link target outside fenced code, with its line."""
    plain = _outside_fences(text)
    return [(plain.count("\n", 0, m.start()) + 1, m.group(1))
            for m in LINK.finditer(plain)]


def anchor(heading: str) -> str:
    """A heading's anchor as GitHub makes it: link syntax reduced to its text,
    lower case, every character but letters, digits, `-`, `_` and spaces
    removed, and spaces turned into `-`."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


def anchors(text: str) -> set[str]:
    """Every heading anchor in a document, with `-1`, `-2` added to repeated
    headings as GitHub does."""
    seen: dict[str, int] = {}
    out = set()
    for line in _outside_fences(text).splitlines():
        m = HEADING.match(line)
        if not m:
            continue
        base = anchor(m.group(1))
        count = seen.get(base, 0)
        seen[base] = count + 1
        out.add(base if count == 0 else f"{base}-{count}")
    return out


def link_problems(rel: str, text: str) -> list[str]:
    """Every link in `text`, the document at `rel`, that points at nothing."""
    owned = owned_paths()
    folder = (REPO / rel).parent
    problems = []
    for line, target in links(text):
        if target.startswith(SKIPPED_SCHEMES):
            continue
        path_part, _, fragment = target.partition("#")
        if path_part:
            resolved = (folder / path_part).resolve()
            try:
                target_rel = resolved.relative_to(REPO.resolve()).as_posix()
            except ValueError:
                target_rel = None
            if target_rel in PENDING_TARGETS:
                continue
            if not resolved.exists():
                problems.append(f"{rel}:{line}: {target}: no such file")
                continue
        else:
            resolved, target_rel = REPO / rel, rel
        # The document being scanned is owned, so its own anchors count too.
        if not fragment or (target_rel != rel and target_rel not in owned):
            continue
        heading_text = text if target_rel == rel else resolved.read_text(encoding="utf-8")
        if fragment not in anchors(heading_text):
            problems.append(f"{rel}:{line}: {target}: no heading with that anchor")
    return problems


@pytest.mark.parametrize("rel", REWRITTEN)
def test_every_link_in_an_owned_document_resolves(rel):
    problems = link_problems(rel, owned_text(rel))
    assert not problems, "broken links:\n  " + "\n  ".join(problems)


def test_the_link_check_reports_a_missing_file():
    problems = link_problems("docs/guide/x.md", "See [the guide](nowhere.md).")
    assert problems == ["docs/guide/x.md:1: nowhere.md: no such file"]


def test_the_link_check_reports_a_missing_heading():
    problems = link_problems("docs/guide/x.md",
                             "See [work](work.md#no-such-heading-anywhere).")
    assert problems == ["docs/guide/x.md:1: work.md#no-such-heading-anywhere: "
                        "no heading with that anchor"]


def test_the_link_check_reports_a_missing_heading_in_the_same_document():
    text = "# Title\n\n## A part\n\nSee [a part](#a-part) and [b](#b-part).\n"
    assert link_problems("docs/guide/x.md", text) == \
        ["docs/guide/x.md:5: #b-part: no heading with that anchor"]


def test_the_link_check_lets_the_pending_migration_guide_through():
    text = "Follow [the guide](../migration-guide-2.8-to-3.0.0.md)."
    assert link_problems("docs/guide/x.md", text) == []
    assert (REPO / PENDING_TARGETS[0]).exists() is False


def test_the_link_check_skips_web_links_and_fenced_code():
    text = ("[a](https://example.com/x) [b](tcw://work/p/x) [c](mailto:a@b.c)\n"
            "```md\n[d](nowhere.md)\n```\n")
    assert link_problems("docs/guide/x.md", text) == []


@pytest.mark.parametrize("heading, expected", [
    ("Why taxonomy and capabilities live in the repository",
     "why-taxonomy-and-capabilities-live-in-the-repository"),
    ("`TCW_PROJECT_<ID>`: where a project is", "tcw_project_id-where-a-project-is"),
    ("Example: keeping git in step (something your project adds)",
     "example-keeping-git-in-step-something-your-project-adds"),
    ("`work.stages.*.post`", "workstagespost"),
])
def test_anchors_are_made_the_way_github_makes_them(heading, expected):
    assert anchor(heading) == expected


def test_a_repeated_heading_gets_a_number():
    assert anchors("## Setup\n\n## Setup\n") == {"setup", "setup-1"}


# ── criterion 4: no allowance entry is named ──────────────────────────────────


def allowance_names(text: str) -> list[str]:
    """Every entry of the five allowance lists that `text` names."""
    named = [e for e in (*REMOVED_COMMANDS, *REMOVED_FORMS, *REFUSED_KEYS)
             if _names(text, e)]
    named += [f"{c} {v}" for c, v in REFUSED_VALUES if _names(text, f"{c} {v}")]
    named += [f"{c} {f}" for c, f in REMOVED_FLAGS if _flag_named(text, c, f)]
    return named


@pytest.mark.parametrize("rel", REWRITTEN)
def test_no_owned_document_names_an_allowance_entry(rel):
    named = allowance_names(owned_text(rel))
    assert not named, f"{rel} names entries of tests/doc_allowance.py: {named}"


def test_the_allowance_check_sees_a_removed_command():
    assert "tcw work stage gate" in allowance_names("Run `tcw work stage gate <slug>`.")


def test_the_allowance_check_sees_a_removed_flag_and_a_refused_key():
    named = allowance_names("`tcw work list --status active` and `work.retain`")
    assert {"tcw work list --status", "work.retain"} <= set(named)


def test_the_agents_section_runs_to_the_next_level_two_heading():
    text = ("# A\n\n## B\n\n" + AGENTS_HEADING + "\n\nbody\n\n### deeper\n\nmore\n"
            "\n## C\n\nafter\n")
    section = agents_worktree_section(text)
    assert section.startswith(AGENTS_HEADING) and "more" in section
    assert "after" not in section


def test_the_agents_section_must_exist():
    with pytest.raises(AssertionError, match="has no line"):
        agents_worktree_section("# A\n\n### Working in a `--worktree` branch\n")


# ── criterion 9: the lifecycle documents ──────────────────────────────────────

ABSTRACTION = REPO / "docs/lifecycle/abstraction.md"

# The four phrases `tests/test_repo_lifecycle.py` checked until TCW-70 deleted
# it (TCW-75 spec, Design 11): module docstrings cite the first.
MOVED_PHRASES = (
    ("docs/lifecycle/abstraction.md",
     "Could a non-filesystem store implement this operation, even if less elegantly?"),
    ("docs/lifecycle/abstraction.md", "Abstract spine, filesystem leverage"),
    ("docs/lifecycle/implementation.md", "don't pre-abstract"),
    ("docs/lifecycle/harness.md", "Agentskills specification"),
)

BACKEND_OPERATIONS = ("create", "read", "list", "update", "set stage", "comment",
                      "rename", "lookup", "read request", "read comments",
                      "current user", "is item folder")


@pytest.mark.parametrize("rel, phrase", MOVED_PHRASES)
def test_the_lifecycle_documents_keep_their_rules(rel, phrase):
    text = " ".join((REPO / rel).read_text(encoding="utf-8").split())
    assert phrase in text, f"{rel} no longer says {phrase!r}"


def test_abstraction_asks_who_owns_a_fact():
    text = " ".join(ABSTRACTION.read_text(encoding="utf-8").split())
    assert "Who owns this fact: the backend, or the repository?" in text


def _bullets_under(text: str, heading: str) -> list[str]:
    """The top-level bullets of the section under `heading`, each its first
    line."""
    _, found, rest = text.partition("\n" + heading + "\n")
    assert found, f"no heading {heading!r}"
    section = re.split(r"^#{1,2} ", rest, maxsplit=1, flags=re.M)[0]
    return [line for line in section.splitlines() if line.startswith("- ")]


def test_the_backend_interface_names_exactly_twelve_operations():
    bullets = _bullets_under(ABSTRACTION.read_text(encoding="utf-8"),
                             "## The backend interface")
    names = [m.group(1) if (m := re.match(r"- \*\*([^*]+)\*\*", b)) else b
             for b in bullets]
    assert names == list(BACKEND_OPERATIONS), names


def test_abstraction_has_no_move_command():
    assert not re.search(r"\bmv\b", ABSTRACTION.read_text(encoding="utf-8"))
