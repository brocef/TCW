"""No live document names a 3.x form outside a passage about moving from 3.x
(TCW-117 spec, Design 9.2; criterion 31).

A live document is every Markdown file `test_documented_cli_surface` checks:
every file git knows about outside the archival trees of its `ARCHIVAL`
(finished work items, changelogs, release notes, the earlier migration guides).
A 3.x form is a command, flag, key, file name or name format that TCW 3.x has
and 4.0 removes or renames; `THREE_X_PATTERNS` in `tests/doc_vocabulary.py`
lists them, matched case-sensitively, so the prose "TCW projects" is not the
command `tcw projects`.

The allowance: a hit passes when its block (a paragraph, a list item or a
table row, as `doc_vocabulary.blocks` cuts them) also names `tcw migrate` or
links the migration guide, because a 4.0 document must still say what a 3.x
project looks like where it says how to move one over. A hit on a line of a
fenced block never passes: a fenced line is a block of its own, and a 3.x
example in a fenced block belongs in the migration guide, which is archival
(spec Design 1.6 (b)).

This repository's own ledgers are left out until TCW-118 migrates them; see
`UNMIGRATED_RECORDS`.
"""
import re

import pytest

from tests.doc_vocabulary import THREE_X_PATTERNS, blocks, scan

# This repository's taxonomy and capability records stay in 3.x form, with
# their 3.x tcw:// links, until TCW-118 migrates the repository at the merge
# (TCW-116 Design 9.3). TCW-118 deletes this tuple after that migration.
UNMIGRATED_RECORDS = ("docs/taxonomy/", "docs/capabilities/")

# A block naming either of these is about moving from 3.x, so it may name a
# 3.x form (spec Design 1.6).
ALLOWANCE = ("tcw migrate", "migration-guide-3.X-to-4.0.0")

_FENCE = re.compile(r"[ \t]*```")


def _fenced_lines(text: str) -> set[int]:
    """The line numbers of every fence line and every line inside a fenced
    block."""
    fenced, inside = set(), False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            fenced.add(number)
            inside = not inside
        elif inside:
            fenced.add(number)
    return fenced


def three_x_problems(rel: str, text: str) -> list[str]:
    """Each 3.x form in `text` outside the allowance, as
    `<rel>:<line>: <what matched> — <reason>`. `rel` is the file's path from
    the repository root; a file under `UNMIGRATED_RECORDS` gives none."""
    if rel.startswith(UNMIGRATED_RECORDS):
        return []
    fenced = _fenced_lines(text)
    allowed: set[int] = set()
    for block in blocks(text):
        if block[0][0] in fenced:
            continue
        whole = " ".join(line for _, line in block)
        if any(word in whole for word in ALLOWANCE):
            allowed.update(number for number, _ in block)
    return [f"{rel}:{hit.line}: {hit.text} — {hit.reason}"
            for hit in scan(text, THREE_X_PATTERNS, flags=0)
            if hit.line not in allowed]


# The spec's table (Design 9.2), one entry per regular expression.
EXPECTED = (
    ("P1", r"tcw (init|provision|projects|config)\b"),
    ("P2", r"tcw work new [^`]*--project\b"),
    ("P3", r"--blocks\b"),
    ("P4", r"--local\b"),
    ("P5", r"extends (add|rm)\b"),
    ("P5", r"(taxonomy|capabilities)\.extends\b"),
    ("P5", r"\bextends:"),
    ("P6", r"\bupstream (project|connection|link|relation)s?\b"),
    ("P6", r"\bupstream:"),
    ("P6", r"projects\.(upstream|parent|children)\b"),
    ("P7", r"(?<![\w-])(meta|item)\.yaml\b"),
    ("P8", r"tcw://[CTW]/"),
    ("P8", r"tcw://[a-z0-9-]+/[CTW]/"),
    ("P9", r"\bcap-[0-9a-f]{6}\b"),
    ("P10", r"\bnot_tags\b"),
    ("P11", r"<project(-id)?>/<"),
    ("P11", r"\btcw/TCW-[0-9]"),
    ("P12", r"^\s*overrides:\s*[^\s./]+/"),
)

# One sample per entry, in the table's order; the last is fenced, since no
# other entry matches it and `^` must start its block.
SAMPLES = (
    "`tcw init --id x`",
    '`tcw work new "t" --project core`',
    "`--blocks`",
    "`--local`",
    "extends add core",
    "taxonomy.extends",
    "extends: [core]",
    "an upstream project",
    "upstream:",
    "projects.upstream",
    "item.yaml",
    "tcw://C/billing",
    "tcw://core/T/billing",
    "cap-1a2b3c",
    "not_tags",
    "<project>/<folder>",
    "tcw/TCW-12-add-export",
    "```\noverrides: core/billing\n```",
)

SCRATCH = "docs/guide/scratch.md"


def _label(reason: str) -> str:
    return reason.split(":", 1)[0]


def test_the_table_is_p1_to_p12():
    assert len(THREE_X_PATTERNS) == 18
    assert [_label(why) for _, why in THREE_X_PATTERNS] == [
        label for label, _ in EXPECTED]
    assert [pattern for pattern, _ in THREE_X_PATTERNS] == [
        pattern for _, pattern in EXPECTED]
    for _, why in THREE_X_PATTERNS:
        assert why.endswith("(scan: TCW-117)"), why


def test_unmigrated_records_are_the_two_ledgers():
    assert UNMIGRATED_RECORDS == ("docs/taxonomy/", "docs/capabilities/")
    source = open(__file__, encoding="utf-8").read()
    assert ("# (TCW-116 Design 9.3). TCW-118 deletes this tuple after that "
            "migration.") in source


@pytest.mark.parametrize("index", range(len(SAMPLES)),
                         ids=[f"{label}-{n}" for n, (label, _) in
                              enumerate(EXPECTED)])
def test_each_pattern_fails_a_scratch_document(index):
    label = EXPECTED[index][0]
    text = f"Some words before {SAMPLES[index]} and after.\n"
    if SAMPLES[index].startswith("```"):
        text = SAMPLES[index] + "\n"
    problems = three_x_problems(SCRATCH, text)
    assert any(f"— {label}:" in p for p in problems), problems


@pytest.mark.parametrize("index", range(len(SAMPLES)),
                         ids=[f"{label}-{n}" for n, (label, _) in
                              enumerate(EXPECTED)])
@pytest.mark.parametrize("beside", (
    "Run `tcw migrate` to convert it.",
    "See [the guide](../migration-guide-3.X-to-4.0.0.md).",
))
def test_the_same_hit_beside_tcw_migrate_passes(index, beside):
    sample = SAMPLES[index]
    if sample.startswith("```"):
        # Unfenced, so the allowance can reach it: `^` starts the block.
        text = f"overrides: core/billing\n{beside}\n"
    else:
        text = f"Some words before {sample} and after.\n{beside}\n"
    assert three_x_problems(SCRATCH, text) == []


@pytest.mark.parametrize("text", (
    "```\nitem.yaml\ntcw migrate\n```\n",
    "```\nitem.yaml  # tcw migrate converts this\n```\n",
))
def test_a_fenced_line_cannot_borrow_the_allowance(text):
    problems = three_x_problems(SCRATCH, text)
    assert len(problems) == 1 and "— P7:" in problems[0], problems


@pytest.mark.parametrize("rel", (
    "docs/capabilities/x/description.md",
    "docs/taxonomy/x/description.md",
))
def test_the_ledgers_are_left_out_while_unmigrated(rel):
    assert three_x_problems(rel, "Each item has an item.yaml.\n") == []


@pytest.mark.parametrize("text", (
    "Each item has a `tcw-work-item.yaml`.\n",
    "```yaml\nprojects:\n  core:\n    path: ../core\n```\n",
    "These are the four TCW projects: core, app, web and docs.\n",
    "```\noverrides: app.capabilities/billing\n```\n",
    "```\noverrides: <full id>\n```\n",
    "Make it with `tcw work new \"t\"`, then `tcw work list --project app`.\n",
    "Personal files: `.tcw/tcw-config.local.yaml` and "
    "`.tcw/tcw-manifest.local.yaml`.\n",
))
def test_4_0_forms_pass(text):
    assert three_x_problems(SCRATCH, text) == []


def test_case_is_kept_for_the_3_0_table_and_dropped_for_the_3_x_table():
    assert scan("TCW WORK START")
    assert scan("TCW projects list", THREE_X_PATTERNS, flags=0) == []
    assert len(scan("tcw projects list", THREE_X_PATTERNS, flags=0)) == 1
