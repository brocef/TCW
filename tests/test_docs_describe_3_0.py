"""The documents TCW-75 owns describe TCW 3.0, and nothing else (TCW-75 spec,
acceptance criteria 1, 2, 3 and 10). Criterion 4's check, that no owned
document names an entry of the temporary documentation allowance, went with
the allowance itself (TCW-76 Design 7).

"Owned documents" are the README, every guide but `web-viewer.md`, the three
lifecycle documents, the `configure` skill, and the section of `AGENTS.md`
headed `### Working in a git worktree` (`CLAUDE.md` is a symbolic link to
`AGENTS.md`, so it is not read again). Three scans read them:

- the 2.x vocabulary scan (criterion 2), with the table TCW-74 wrote in
  `tests/doc_vocabulary.py`, shared with its own scan of the skills;
- the link check (criterion 3): every relative Markdown link points at a file
  that exists, and an `#anchor` into an owned document at a heading in it;
- the command check: every `tcw …` invocation resolves in the 3.0 parser,
  procedure and stage names included, with the same `command_problem` TCW-74's
  scan of the skills uses. The argument parser alone accepts any word as a
  procedure name, so `tcw work procedure prompt <id>` is caught only here.

The scans read every owned document, found by glob (`OWNED`), and a test pins
that set, so a guide added later is a decision to scan it rather than an
accident.
"""

import re
from pathlib import Path

import pytest

from tests.doc_vocabulary import PATTERNS, scan
from tests.test_documented_cli_surface import _invocations
from tests.test_shipped_text import command_problem

REPO = Path(__file__).resolve().parent.parent

AGENTS = "AGENTS.md"
AGENTS_HEADING = "### Working in a git worktree"


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
    """What the scans read for one entry of `OWNED`."""
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


# The owned documents, by path from the repository root. `AGENTS.md` stands for
# its worktree section only (`agents_worktree_section`).
OWNED: tuple[str, ...] = tuple(sorted(owned_paths()))


def test_the_scans_read_exactly_the_owned_documents():
    assert set(OWNED) == {
        AGENTS,
        "README.md",
        "docs/guide/cli.md",
        "docs/guide/configuration.md",
        "docs/guide/jira.md",
        "docs/guide/linking-and-validation.md",
        "docs/guide/multi-repo.md",
        "docs/guide/taxonomy-and-capabilities.md",
        "docs/guide/work.md",
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
    }


# ── criterion 10: the inventory was carried out ───────────────────────────────


@pytest.mark.parametrize("rel", ("docs/work-inbox-template.md",
                                 "skills/configure/references/tracker.md"))
def test_a_retired_document_is_gone(rel):
    assert not (REPO / rel).exists(), f"{rel} still exists"


@pytest.mark.parametrize("rel", ("docs/guide/cli.md",
                                 "docs/guide/examples/commit-item-after-move.sh",
                                 "skills/configure/references/personal.md"))
def test_a_new_document_exists(rel):
    assert (REPO / rel).is_file(), f"{rel} is missing"


# ── criterion 2: no 2.x vocabulary ────────────────────────────────────────────


def vocabulary_problems(rel: str, text: str) -> list[str]:
    """Every match of criterion 2's table, one line each. The table alone:
    `builtin: true` is not in it, since `tcw config show` prints it."""
    lines = text.splitlines()
    return [f"{rel}:{h.line}: {h.text!r} ({h.reason}): {lines[h.line - 1].strip()}"
            for h in scan(text, PATTERNS)]


@pytest.mark.parametrize("rel", OWNED)
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


@pytest.mark.parametrize("rel", OWNED)
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


# ── every command named exists ────────────────────────────────────────────────


def command_problems(text: str) -> list[str]:
    """Each `tcw …` invocation in `text` that does not resolve, with why."""
    return [f"`{span}`: {problem}" for span in _invocations(text)
            if (problem := command_problem(span)) is not None]


@pytest.mark.parametrize("rel", OWNED)
def test_every_command_in_an_owned_document_exists(rel):
    problems = command_problems(owned_text(rel))
    assert not problems, f"{rel} names commands that do not exist:\n  " + \
        "\n  ".join(problems)


@pytest.mark.parametrize("text", [
    "Run `tcw work procedure prompt pause-work`.",
    "```sh\ntcw work procedure prompt pause-work\n```\n",
    "Run `tcw work stage gate plan <slug>`.",
    "Run `tcw work list --status active`.",
])
def test_the_command_check_sees_a_command_that_does_not_exist(text):
    assert command_problems(text)


def test_the_command_check_skips_minus_c():
    assert not command_problems('Run `tcw -C tcw://<id>.path/ work new "<title>" '
                                '--parent <slug> --nest`.')
    assert command_problems("Run `tcw -C <target> work new --no-such-flag`.")


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
                      "move", "lookup", "read request", "read comments",
                      "current user", "is item folder")


@pytest.mark.parametrize("rel, phrase", MOVED_PHRASES)
def test_the_lifecycle_documents_keep_their_rules(rel, phrase):
    text = " ".join((REPO / rel).read_text(encoding="utf-8").split())
    assert phrase in text, f"{rel} no longer says {phrase!r}"


def test_harness_points_at_where_a_subagent_is_never_required():
    """TCW-76 review round 2, D3: `harness.md` names the section that says a
    subagent is never required, and that section says so. The link check
    above reads anchors only in owned documents, and the work skill is not
    one, so the anchor is checked here."""
    text = " ".join((REPO / "docs/lifecycle/harness.md").read_text(encoding="utf-8").split())
    assert ("a subagent is permitted, never required: a session that cannot dispatch runs "
            "the same stage itself (the `work` skill's [Rules no project text changes]"
            "(../../skills/work/SKILL.md#rules-no-project-text-changes))") in text
    skill = (REPO / "skills/work/SKILL.md").read_text(encoding="utf-8")
    assert "rules-no-project-text-changes" in anchors(skill)
    rules = skill.split("\n## Rules no project text changes\n", 1)[1].split("\n## ", 1)[0]
    assert ("A subagent is permitted, never required: a session that cannot dispatch "
            "runs the same stage itself.") in " ".join(rules.split())


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


# ── criterion 1: the README's structure ───────────────────────────────────────

README = REPO / "README.md"


def _level_two_headings(text: str) -> list[str]:
    return [line[3:].strip() for line in _outside_fences(text).splitlines()
            if line.startswith("## ")]


def _section(text: str, heading: str) -> str:
    """The text under `heading`, up to the next heading of the same level or
    higher."""
    level = len(heading) - len(heading.lstrip("#"))
    lines = _outside_fences(text).splitlines()
    start = lines.index(heading)
    end = next((i for i in range(start + 1, len(lines))
                if (m := re.match(r"^(#{1,6}) ", lines[i]))
                and len(m.group(1)) <= level), len(lines))
    return "\n".join(lines[start + 1:end])


def test_the_section_after_the_overview_says_why_the_records_live_in_the_repository():
    headings = _level_two_headings(README.read_text(encoding="utf-8"))
    after = headings[headings.index("Overview") + 1]
    assert after == "Why taxonomy and capabilities live in the repository"


def test_every_contents_link_points_at_a_readme_heading():
    text = README.read_text(encoding="utf-8")
    contents = _section(text, "## Contents")
    targets = [target for _, target in links(contents)]
    assert targets, "the Contents list has no links"
    missing = [t for t in targets if t.lstrip("#") not in anchors(text)]
    assert not missing, missing


def test_the_work_section_has_a_filesystem_and_then_a_jira_heading():
    work = _section(README.read_text(encoding="utf-8"), "## Work")
    found = [(len(m.group(1)), m.group(2)) for line in work.splitlines()
             if (m := re.match(r"^(#{3,6}) (Filesystem|Jira)\b", line))]
    assert [name for _, name in found] == ["Filesystem", "Jira"], found
    assert found[0][0] == found[1][0], found


def test_the_web_app_and_the_cli_requirements_do_not_need_node():
    text = README.read_text(encoding="utf-8")
    assert "Node.js" not in _section(text, "## TCW Local Web App")
    requirements = next(p for p in _section(text, "### CLI").split("\n\n")
                        if p.startswith("Requires"))
    assert "Node.js" not in requirements


def test_the_documentation_index_links_the_guides_it_must():
    index = {target for _, target in
             links(_section(README.read_text(encoding="utf-8"), "## Documentation"))}
    for must in ("docs/migration-guide-2.8-to-3.0.0.md",
                 "docs/migration-guide-2.4.X-to-2.5.0.md", "docs/guide/cli.md"):
        assert must in index, must
    assert "docs/work-inbox-template.md" not in index



def test_the_abstraction_document_bounds_an_object_folder_by_resources():
    """TCW-111 AC 19 (Design 9.1)."""
    text = " ".join(ABSTRACTION.read_text(encoding="utf-8").split())
    assert ("treating an object's folder as an open set of files — _it is bounded: "
            "its state file and fixed files") in text
    assert "and one `resources/` folder for anything else" in text
    assert "`item.yaml`" not in text
    interface = " ".join(_bullets_under(ABSTRACTION.read_text(encoding="utf-8"),
                                        "## The backend interface"))
    assert "id-path" in interface
    assert "Where a folder sits never declares a parent; `parent` does." in text


def test_the_backend_docstring_counts_twelve_operations():
    import tcw.work.backend
    assert "Twelve operations" in tcw.work.backend.__doc__


def test_abstraction_names_move_and_no_rename_and_no_uncommitted_check():
    """TCW-114 Design 9.3, AC 23."""
    text = " ".join((REPO / "docs/lifecycle/abstraction.md").read_text(
        encoding="utf-8").split())
    assert "- **move**: change an item's id-path" in text
    assert "- **rename**:" not in text
    assert "uncommitted changes before creating an item in another project" not in text
