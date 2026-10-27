"""The 3.x to 4.0 migration guide says what TCW-117's acceptance criteria
require of it, as far as a test can check (TCW-117 spec, Design 9.4;
criteria 1, 5 and 7).

What cannot be checked here is whether a reader can follow the guide; the cold
read at qa checks that (spec Design 9.7).

A **mapping table** is a table whose header's first cell begins with `3.x`:
its first column holds a 3.x form, its second what replaces it. The guide's
path starts `docs/migration-guide-`, which `test_documented_cli_surface`
treats as archival and skips, so its commands are checked here instead:
every one outside a mapping table's first column and the epic-parts table's
3.x column must resolve in the surface 4.0 shows in `--help`.
"""

import re

import pytest

from tests.doc_vocabulary import THREE_X_PATTERNS
from tests.test_docs_describe_3_0 import link_problems
from tests.test_documented_cli_surface import REPO, _check, _invocations, _walk
from tests.test_migration_guide import cells, section, sections, tables
from tests.test_shipped_text import command_problem

GUIDE_REL = "docs/migration-guide-3.X-to-4.0.0.md"
GUIDE = (REPO / GUIDE_REL).read_text(encoding="utf-8")

SECTIONS = [
    "Before you start",
    "Migrating one project",
    "Migrating related projects",
    "What each 3.x name becomes",
    "The epic-parts flow, step by step",
    "Personal settings and environment variables",
    "Where provisioning may place a clone",
    "Scripts, hooks and agent instructions",
]

# Every 3.x name the guide must map (spec Design 2.6 (a) to (g)).
THREE_X_NAMES = (
    "tcw init", "tcw projects list", "tcw config show", "tcw provision",
    "tcw work new --project", "tcw work edit --blocks", "--local",
    "tcw taxonomy extends add", "tcw taxonomy extends rm",
    "tcw capabilities extends add", "tcw capabilities extends rm",
    "taxonomy.extends", "capabilities.extends",
    "tcw-config.yaml", "tcw-config.local.yaml", "not_tags",
    "projects.parent", "projects.children", "projects.upstream",
    "projects.<id>.repository", "projects.<id>.jira",
    "work.path: /", "work.path: ~", "<component>.repository",
    "meta.yaml", "item.yaml", "overrides:", "cap-1a2b3c",
    "<project>/<folder>", "tcw://C/", "tcw://W/", "tcw://T/",
    "tcw://core/T/", "TCW Item", '"schema": 1',
    "# <layer>: <file>",
)

EPIC_SECTION = "The epic-parts flow, step by step"


def _plain(cell: str) -> str:
    return cell.replace("`", "").strip()


def mapping_tables(text: str = GUIDE) -> list[list[list[str]]]:
    return [t for t in tables(text) if _plain(t[0][0]).startswith("3.x")]


def first_cells() -> list[str]:
    return [_plain(row[0]) for t in mapping_tables() for row in t[1:]]


def epic_table() -> list[list[str]]:
    body = section(GUIDE, 2, EPIC_SECTION)
    found = [t for t in tables(body)
             if [_plain(c) for c in t[0][:3]] == ["#", "3.x step", "4.0"]]
    assert len(found) == 1, f"expected one epic-parts table, found {len(found)}"
    return found[0]


def _blank_cell(line: str, index: int) -> str:
    """`line`, a table row, with its cell number `index` blanked."""
    parts = re.split(r"(?<!\\)\|", line)
    # parts[0] is what precedes the first bar; cell n is parts[n + 1].
    parts[index + 1] = " " * len(parts[index + 1])
    return "|".join(parts)


def exempt_blanked(text: str = GUIDE) -> str:
    """The guide with every mapping table's first cell and the epic-parts
    table's 3.x cell blanked: those cells name 3.x commands on purpose."""
    out, in_mapping, in_epic, epic = [], False, False, False
    for line in text.splitlines():
        if line.startswith("## "):
            epic = line[3:].strip() == EPIC_SECTION
        if not line.startswith("|"):
            in_mapping = in_epic = False
            out.append(line)
            continue
        if not (in_mapping or in_epic):
            header = [_plain(c) for c in cells(line)]
            in_mapping = header[0].startswith("3.x")
            in_epic = epic and header[:3] == ["#", "3.x step", "4.0"]
        if in_mapping:
            line = _blank_cell(line, 0)
        elif in_epic:
            line = _blank_cell(line, 1)
        out.append(line)
    return "\n".join(out)


@pytest.fixture(scope="module")
def tree() -> dict[tuple, set[str]]:
    """Every `tcw …` command path 4.0's `--help` shows, with its flags."""
    out: dict[tuple, set[str]] = {}
    _walk([], out)
    return out


def _resolve(span: str, tree) -> str | None:
    return _check(span, tree) or command_problem(span)


def test_the_sections_are_in_order():
    assert [h for h, _ in sections(GUIDE, 2)] == SECTIONS


@pytest.mark.parametrize("name", THREE_X_NAMES)
def test_every_3x_name_has_a_row(name):
    assert any(name in cell for cell in first_cells()), (
        f"no mapping row's first cell names {name!r}")


def test_every_row_says_what_replaces_it():
    empty = [row[0] for t in mapping_tables() for row in t[1:]
             if len(row) < 2 or not row[1].strip()]
    assert mapping_tables() and not empty, empty


def test_every_4_0_command_resolves(tree):
    spans = _invocations(exempt_blanked())
    assert spans
    problems = [f"`{s}`: {p}" for s in spans if (p := _resolve(s, tree))]
    assert not problems, "\n  ".join(["4.0 does not accept:", *problems])


@pytest.mark.parametrize("span", (
    'tcw work new "t" --project app',
    "tcw work edit x --blocks y",
    "tcw capabilities list --local",
))
def test_a_hidden_flag_is_refused(tree, span):
    assert _resolve(span, tree) is not None


def test_the_epic_table_has_rows_a_to_f():
    assert [_plain(row[0]) for row in epic_table()[1:]] == list("abcdef")


def test_the_exit_table_is_0_1_2_3_5():
    body = section(GUIDE, 2, "Migrating one project")
    found = [t for t in tables(body) if _plain(t[0][0]) == "Exit"]
    assert len(found) == 1
    assert [_plain(row[0]) for row in found[0][1:]] == ["0", "1", "2", "3", "5"]


def test_every_link_resolves():
    assert link_problems(GUIDE_REL, GUIDE) == []


@pytest.mark.parametrize("pattern, why", THREE_X_PATTERNS,
                         ids=[why.split(":")[0] + "-" + str(n)
                              for n, (_, why) in enumerate(THREE_X_PATTERNS)])
def test_every_scan_pattern_has_a_row(pattern, why):
    regex = re.compile(pattern)
    assert any(regex.search(cell) for cell in first_cells()), (
        f"no mapping row's first cell is an example of {why}")


def test_before_you_start_links_the_2_8_guide():
    assert "(migration-guide-2.8-to-3.0.0.md)" in section(
        GUIDE, 2, "Before you start")


def test_related_projects_come_first():
    body = section(GUIDE, 2, "Migrating one project").strip()
    first = body.split("\n\n", 1)[0]
    assert ("Migrating related projects" in first
            or "#migrating-related-projects" in first), first


# -- the ready search for removed commands and flags (evaluator finding 8) ---------

SCRIPTS_SECTION = "Scripts, hooks and agent instructions"


def removed_search_pattern() -> str:
    """The one regular expression of the guide's ready search, a
    `grep -rnE --exclude-dir=.git '<pattern>' .` line in a fenced block."""
    body = section(GUIDE, 2, SCRIPTS_SECTION)
    found = re.findall(r"^ *grep -rnE --exclude-dir=\.git '([^']+)' \.$", body, re.M)
    assert len(found) == 1, f"expected one ready search, found {found}"
    return found[0]


def removed_lines() -> list[str]:
    """A command line for each row of the guide's 3.x command and flag
    tables, its placeholders filled in."""
    body = section(GUIDE, 2, "What each 3.x name becomes")
    out = []
    for table in tables(body):
        if _plain(table[0][0]) not in ("3.x command", "3.x flag"):
            continue
        for row in table[1:]:
            spans = re.findall(r"`([^`]+)`", row[0])
            if " as in " in row[0]:
                lines = [spans[-1]]                 # `--project`, as in `tcw work new …`
            elif spans[0].startswith("--"):
                lines = [f"{s} {spans[0]}" for s in spans[1:]]   # `--local` on `…`
            else:
                lines = [spans[0]]
            out += [re.sub(r"<[^>]+>", "x1", line) for line in lines]
    return out


def _grep_matches(pattern: str, lines: list[str]) -> set[str]:
    """The lines `grep -E` itself matches, so the test checks the search as
    a reader runs it rather than Python's reading of the pattern."""
    import subprocess
    r = subprocess.run(["grep", "-E", pattern], input="\n".join(lines) + "\n",
                       capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    return set(r.stdout.splitlines())


def test_the_ready_search_finds_every_removed_command_and_flag():
    lines = removed_lines() + [
        # as a script or an agent instruction might write them
        'tcw work new --project core "Fix it"',
        "tcw projects list --json",
        "tcw init --id app",
        "tcw provision",
        "tcw work edit A-1 --blocks B-2",
        "tcw capabilities list --local --json",
        "`tcw config show`",
    ]
    assert len(removed_lines()) >= 11, removed_lines()
    missed = [line for line in lines
              if line not in _grep_matches(removed_search_pattern(), lines)]
    assert not missed, missed


def test_the_ready_search_finds_no_current_command():
    current = _invocations(exempt_blanked()) + [
        "tcw project new --id app",
        "tcw project list",
        "tcw project config --origin",
        "tcw project provision",
        "tcw project path core",
        'tcw -C ../core work new "Fix it"',
        "tcw -C tcw://core.path/ work new t",
        "tcw work edit B-2 --blocked-by A-1",
        "tcw taxonomy list --scope up",
        "tcw capabilities list",
        "tcw migrate --no-jira",
        "cat .tcw/tcw-config.local.yaml",
    ]
    assert len(current) > 20
    wrong = _grep_matches(removed_search_pattern(), current)
    assert not wrong, sorted(wrong)
