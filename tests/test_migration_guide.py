"""The 2.8 to 3.0.0 migration guide says what TCW-76's acceptance criteria
require of it, as far as a test can check (TCW-76 spec, criteria 1 to 10 and
32; plan, choice 1).

What cannot be checked here is whether an agent can follow the guide; the
rehearsal and TCW's own migration check that.

A **mapping table** is a table whose header's first cell begins with `2.x`
or `2.8`: its first column holds 2.x names, its second what each becomes.
"""

import re
from pathlib import Path

import pytest

from tests.test_docs_describe_3_0 import link_problems

REPO = Path(__file__).resolve().parent.parent
GUIDE_REL = "docs/migration-guide-2.8-to-3.0.0.md"
GUIDE = (REPO / GUIDE_REL).read_text(encoding="utf-8")

FENCE = re.compile(r"^```.*?^```", re.M | re.S)
SPAN = re.compile(r"`([^`\n]+)`")


def _outside_fences(text: str) -> str:
    """The text with every fenced block blanked, keeping every offset."""
    return FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def sections(text: str, level: int) -> list[tuple[str, str]]:
    """`(heading, body)` for each heading of exactly `level` `#`s, the body
    running to the next heading of that level or higher. Headings inside
    fenced blocks are not headings."""
    plain = _outside_fences(text)
    marks = [(m.start(), m.end(), m.group(2)) for m in
             re.finditer(r"^(#{1,%d}) (.*)$" % level, plain, re.M)]
    out = []
    for i, (start, end, title) in enumerate(marks):
        if len(plain[start:end].split(" ", 1)[0]) != level:
            continue
        stop = next((s for s, _, _ in marks[i + 1:]), len(text))
        out.append((title.strip(), text[end:stop]))
    return out


def section(text: str, level: int, title: str) -> str:
    found = [body for heading, body in sections(text, level) if heading == title]
    assert len(found) == 1, f"expected one {'#' * level} {title!r}, found {len(found)}"
    return found[0]


def cells(row: str) -> list[str]:
    """A table row's cells, with `\\|` kept as a literal bar."""
    inner = row.strip()[1:-1].replace("\\|", "\0")
    return [c.strip().replace("\0", "|") for c in inner.split("|")]


def tables(text: str) -> list[list[list[str]]]:
    """Every table outside fenced code: header row first, separator dropped."""
    found, current = [], []
    for line in _outside_fences(text).splitlines():
        if line.startswith("|"):
            current.append(line)
        elif current:
            found.append(current)
            current = []
    if current:
        found.append(current)
    return [[cells(r) for r in t if not re.match(r"^\|[\s|:-]+\|$", r)] for t in found]


def mapping_tables(text: str = GUIDE) -> list[list[list[str]]]:
    return [t for t in tables(text) if re.match(r"2\.(x|8)\b", t[0][0])]


def mapping_rows(text: str = GUIDE) -> list[list[str]]:
    return [row for table in mapping_tables(text) for row in table[1:]]


def first_column_spans(text: str = GUIDE) -> list[str]:
    return [span for row in mapping_rows(text) for span in SPAN.findall(row[0])]


# -- Criterion 4: every 2.x name is in the first column of a mapping row ---------------

# Written out by hand, because the constants they come from no longer exist on
# the 3.0 branch. Every location is in the 2.x code at the tag `v2.8.1`.
TWO_X_NAMES = (
    # `TRACKER_KEYS`, tcw/store/base.py:1359-1363
    "provider", "base-url", "candidate-query", "credentials",
    "exclusive-claim-transition", "transitions", "statuses", "strict",
    "timeout-seconds", "comments", "link", "inbox-query", "create", "pre-backlog",
    # `TRACKER_CREATE_KEYS`, tcw/store/base.py:1364-1365
    "project", "issue-type", "issue-types", "components", "on-new",
    # `TRACKER_TRANSITION_KEYS`, tcw/store/base.py:1381
    "start", "submit", "rework", "complete", "discard",
    # the `work.lifecycle` keys, tcw/store/base.py:2982
    "stages", "transitions", "timeout", "artifacts", "output-cap",
    # `STAGE_IDS`, tcw/store/base.py:1136
    "inbox", "request", "spec", "plan", "implement", "verify", "postmortem",
    # `TRANSITION_IDS`, tcw/store/base.py:1155-1156
    "start", "submit", "complete", "rework", "discard", "auto-delete",
    # the `work` keys read at tcw/store/fs.py:7323, :7334, :7349, :7688
    "retain", "auto-commit-transitions", "publish-transitions", "trunk-branch",
    # the `state.yaml` fields read at tcw/store/fs.py:5491-5512
    "title", "created", "resolution", "priority", "effort", "complexity", "tags",
    "blocked_by", "initiative", "type", "worktree", "branch", "parent", "owner",
    "started",
    # the `tracker.yaml` keys, `classify_binding`, tcw/store/base.py:469-510
    "schema", "provider", "project", "part", "ticket", "bound", "unlinked", "sync",
    "comment", "status-synced", "catch-up", "owed", "created",
    # `WORK_ARTIFACTS`, tcw/store/base.py:3101-3102, as files
    "initial-request.md", "spec.md", "plan.md", "outcome.md", "refined-outcome.md",
    "rework.md", "post-mortem.md", "intake.md",
    # `WORK_SIDECARS`, tcw/store/base.py:3113-3139
    "capabilities.yaml", "rollup.md", "tracker.yaml",
    # the store-root files: `GRAVEYARD_NAME`, `dod.yaml`, `RENAMES_NAME`
    # (tcw/store/fs.py:6538)
    "graveyard.yaml", "dod.yaml", "renames.yaml",
    # `WORK_STATUSES`, tcw/store/base.py:989, the leftover `blocked/`, and the inbox
    "backlog/", "active/", "review/", "completed/", "discarded/", "blocked/", "inbox/",
    # the hook variables set at tcw/work/hooks.py:60-69
    "TCW_SLUG", "TCW_STATUS", "TCW_TRANSITION", "TCW_NODE_ROOT", "TCW_ITEM_PATH",
    "TCW_RESOLUTION",
    # the variables a `generate` binding gets, tcw/work/resolve.py:191-196
    "TCW_HOOK_ROLE", "TCW_HOOK_KIND", "TCW_HOOK_ID", "TCW_HOOK_PHASE",
    # the skills and agents the plugin had at v2.8.1 and the 3.0 branch does not
    # (`git ls-tree --name-only v2.8.1 skills/ agents/`; TCW-76 Design 3.10)
    "commands-verify-work", "post-mortem", "work-stage", "verifier",
)


def _subject(name: str, span: str) -> bool:
    """`span` names `name` itself: it is the name, or a dotted key ending in
    it or passing through it (`work.tracker.create.project` for `create`)."""
    return span == name or span.endswith(f".{name}") or f".{name}." in span


@pytest.mark.parametrize("name", sorted(set(TWO_X_NAMES)))
def test_every_2x_name_is_in_a_mapping_rows_first_column(name):
    rows = [r for r in mapping_rows()
            if any(_subject(name, s) for s in SPAN.findall(r[0]))]
    assert rows, f"no mapping row names `{name}` in its first column"
    # Criterion 4's own check: the row's first cell, read as a table row.
    assert re.search(rf"^\| [^|]*{re.escape(name)}", GUIDE, re.M)
    for row in rows:
        assert len(row) >= 2 and row[1], f"the row for `{name}` says nothing: {row}"


def test_every_mapping_row_says_what_its_name_becomes():
    for row in mapping_rows():
        assert len(row) >= 2 and all(row[1:]), row


# -- Criterion 5: hook variables by meaning ---------------------------------------------

def hook_rows() -> list[list[str]]:
    return mapping_tables(section(GUIDE, 3, "Hook variables"))[0][1:]


def _row(first: str) -> list[str]:
    found = [r for r in hook_rows() if first in r[0]]
    assert len(found) == 1, f"expected one hook row with {first!r}, found {found}"
    return found[0]


def test_tcw_status_in_a_pre_hook_is_the_stage_left():
    row = _row("`TCW_STATUS` in a transition's `pre` hook")
    assert "`TCW_FROM_STAGE`" in row[1] and "`TCW_STAGE`" not in row[1]


def test_tcw_status_in_a_post_hook_is_the_stage_entered():
    row = _row("`TCW_STATUS` in a transition's `post` hook")
    assert "`TCW_STAGE`" in row[1] and "`TCW_FROM_STAGE`" not in row[1]


def test_tcw_status_in_a_stage_gate_is_the_stage_left():
    row = _row("`TCW_STATUS` in a stage's `pre` hook")
    assert row[1].startswith("`TCW_FROM_STAGE`")


def test_tcw_transition_is_the_stage_entered():
    row = _row("`TCW_TRANSITION`")
    assert row[1].startswith("`TCW_STAGE`") and "`TCW_FROM_STAGE`" not in row[1]


def test_tcw_slug_keeps_its_name_and_becomes_the_full_slug():
    row = _row("`TCW_SLUG`")
    assert row[1].startswith("`TCW_SLUG`")
    assert "full slug `<project>/<folder>`" in row[1]


def test_the_hook_table_says_it_maps_by_meaning():
    assert "mapped by what they mean, not by their position" in \
        section(GUIDE, 3, "Hook variables")


# -- Criterion 6: the `artifacts` rule, and status values per hook -----------------------

def test_the_artifacts_row_points_at_the_rule():
    [row] = [r for r in mapping_rows() if "`work.lifecycle.artifacts.<document>`" in r[0]]
    assert "(#templates-become-prompt-entries)" in row[1]


def test_a_tags_only_condition_becomes_not_tags_on_later_entries():
    text = section(GUIDE, 4, "Templates become prompt entries")
    assert "**When every earlier entry's condition is `tags` alone**" in text
    assert "add those tags to each later entry's `not_tags`" in text
    assert "**Any other shape**" in text and "list it\nin the plan" in text


def test_the_rule_shows_this_repositorys_spec_templates():
    text = section(GUIDE, 4, "Templates become prompt entries")
    before, after = [b for b in FENCE.findall(text) if "templates/spec" in b]
    assert "artifacts:" in before and "not_tags" not in before
    assert "- file: docs/lifecycle/templates/spec-bug.md\n" \
           "                  when: { tags: [bug] }" in after
    assert "- file: docs/lifecycle/templates/spec.md\n" \
           "                  when: { not_tags: [bug] }" in after


def test_status_values_are_translated_by_the_hooks_new_stage():
    text = section(GUIDE, 4, "Status values inside comparisons")
    assert "**by the 3.0 stage the hook ends up bound to**" in text
    assert "A former `submit`\n  `post` hook testing `$TCW_STATUS = review`" in text
    assert "tests `$TCW_STAGE = review`, not `qa`" in text


# -- Criterion 8: verdict rounds ----------------------------------------------------------

def document_row(name: str) -> list[str]:
    [row] = [r for r in mapping_rows() if r[0] == f"`{name}`"]
    return row


@pytest.mark.parametrize("name, verdict", [("refined-outcome.md", "accepted"),
                                           ("rework.md", "rejected")])
def test_acceptance_history_maps_to_qa_rounds(name, verdict):
    row = document_row(name)
    assert row[1] == f"`qa/round-N.md` with `verdict: {verdict}`"
    assert row[2] == "a ticket comment"


def test_judges_is_1_with_an_outcome_and_0_without():
    text = section(GUIDE, 4, "Acceptance history goes to qa")
    assert "It is\n  `judges: 1` when the item has `outcome.md`, and `judges: 0` when it has\n  none." \
        in text


# -- Links ---------------------------------------------------------------------------------

def test_every_link_in_the_guide_resolves():
    problems = link_problems(GUIDE_REL, GUIDE)
    assert not problems, "broken links:\n  " + "\n  ".join(problems)
