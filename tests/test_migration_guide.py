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
    assert "**Any other shape**" in text and "list it in the plan" in " ".join(text.split())


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


# -- Criterion 1: the guide opens with its prerequisites and rules ------------------------

def top_headings() -> list[str]:
    return [heading for heading, _ in sections(GUIDE, 2)]


def test_the_first_two_sections_are_the_prerequisites_and_the_rules():
    assert top_headings()[:2] == ["Before you start", "Rules"]


def test_the_prerequisites_and_rules_come_before_any_mapping_table():
    first_table = GUIDE.index("\n| 2.")
    assert GUIDE.index("\n## Rules\n") < first_table
    assert GUIDE.index("\n## Before you start\n") < first_table


@pytest.mark.parametrize("prerequisite", [
    "**The project is on 2.8.x.**",
    "**The 3.0 CLI is installed, beside 2.8.**",
    "**The working tree has no uncommitted changes**",
    "**No 2.x item worktree is open.**",
    "`git worktree list | grep -E '\\[work/'`",
    "**A branch or tag marks the 2.x state**",
    "**Every connected project is on this machine, and is migrated with this one.**",
    "**In Jira mode, `jq` 1.6 or later is installed**",
])
def test_each_prerequisite_is_named(prerequisite):
    assert prerequisite in " ".join(section(GUIDE, 2, "Before you start").split())


def test_the_rules_say_order_then_check_then_stop():
    rules = section(GUIDE, 2, "Rules")
    order = rules.index("1. **Do the steps in order**")
    check = rules.index("2. **After each step, run its check")
    stop = rules.index("3. Stop and ask the user")
    assert order < check < stop


# -- Criterion 2: steps 0 to 12, each with a check ----------------------------------------

def steps() -> list[tuple[str, str]]:
    return sections(section(GUIDE, 2, "The steps"), 3)


def step(number: int) -> str:
    [body] = [b for h, b in steps() if h.startswith(f"Step {number}: ")]
    return body


def check(number: int) -> str:
    """A step's check: from its `**Check:**` paragraph to the end of the step."""
    body = step(number)
    assert body.count("\n**Check:**") == 1, f"step {number} has no single check"
    return body[body.index("\n**Check:**"):]


def test_the_steps_are_0_to_12_in_order():
    numbers = [int(re.match(r"Step (\d+): ", h).group(1)) for h, _ in steps()]
    assert numbers == list(range(13))


@pytest.mark.parametrize("number", range(13))
def test_every_step_has_one_check(number):
    check(number)


@pytest.mark.parametrize("number", [n for n in range(13) if n != 2])
def test_every_check_but_step_2s_has_a_command_and_its_output(number):
    text = check(number)
    assert SPAN.search(text) or FENCE.search(text), f"step {number}'s check has no command"
    assert re.search(r"\b(prints|exits|ends with)\b", text), \
        f"step {number}'s check gives no expected output"


def test_step_2s_check_is_the_reading_at_the_end_of_step_3():
    assert "is the Jira-workflow reading at the end of step 3" in check(2)


def test_step_1s_check_counts_the_approved_plan():
    assert "`grep -c '^## Approved plan' <log>` prints `1`" in check(1)


@pytest.mark.parametrize("number", [4, 5, 6, 7])
def test_no_check_before_step_8_needs_the_inbox_gone(number):
    text = check(number)
    assert "grep -x inbox" not in text and "-name inbox" not in text


def test_step_8s_check_is_that_the_inbox_is_gone():
    assert "`ls docs/work | grep -x inbox` prints nothing" in check(8)


def test_steps_9_and_10_check_only_their_scope():
    assert "without what it\nskips" in check(9)
    assert "<hook files>" in check(10)
    assert "`<hook files>`" in step(1)


# -- Criterion 3: the four stops, and no question per item --------------------------------

STOP = "**Stop and ask**"


def test_stop_and_ask_is_in_steps_1_2_and_12_only():
    where = [n for n in range(13) if STOP in step(n)]
    assert where == [1, 2, 12]
    assert GUIDE.count(STOP) == 3


def test_the_rules_state_the_stop_for_a_failing_check():
    rules = section(GUIDE, 2, "Rules")
    assert "**a check that fails after one retry**" in rules
    assert "ask nothing item by\n   item" in rules


# -- Behavior that changed in commands that kept their names -------------------------------

@pytest.mark.parametrize("topic", [
    "**A slug given to `tcw taxonomy add --slug` must be a slug**",
    "**The viewer's record edits need a revision.**",
    "**`tcw provision` turns git's prompts off.**",
    "**An ssh command the user has set**",
    "**`tcw provision` refuses a configuration it cannot read.**",
    "**The Jira client does not pass credentials on through a redirect.**",
    "**`tcw work` commands check the connected projects.**",
    "**Offline `tcw validate` in Jira mode reads each item's\n  `capabilities.yaml`.**",
])
def test_each_stricter_behavior_is_named(topic):
    assert topic in section(GUIDE, 4, "Behavior that changed")


# -- Criterion 7: behavior that had no key -------------------------------------------------

@pytest.mark.parametrize("topic", ["**Automatic commits.**", "**Publishing.**",
                                   "**Retention.**", "**Ignored completed and discarded folders.**"])
def test_behavior_with_no_key_is_named(topic):
    assert topic in section(GUIDE, 2, "2.x behavior that had no key")


# -- Criterion 9: no harness-only syntax, and a REST form for every Jira write ------------

def test_no_shell_escape_and_no_slash_command():
    assert "!`" not in GUIDE
    slash = [s for s in SPAN.findall(GUIDE) if re.match(r"^/[a-z][a-z0-9-]*(:[a-z0-9-]+)?$", s)]
    assert not slash, slash


@pytest.mark.parametrize("action, form", [
    ("Search", "/rest/api/3/search/jql"),
    ("Create a ticket", "-X POST -H 'Content-Type: application/json' \"$SITE/rest/api/3/issue\""),
    ("List a ticket's transitions", "/transitions\""),
    ("Move a ticket", "-X POST -H 'Content-Type: application/json' \"$SITE/rest/api/3/issue/$KEY-42/transitions\""),
    ("Set fields", "-X PUT"),
    ("List a ticket's comments", "/rest/api/3/issue/$KEY-42/comment?startAt=0&maxResults=100"),
    ("Post a comment", "-X POST -H 'Content-Type: application/json' \"$SITE/rest/api/3/issue/$KEY-42/comment\""),
    ("Link a blocker", "/rest/api/3/issueLink"),
])
def test_every_jira_read_and_write_has_a_rest_form_and_a_web_equivalent(action, form):
    [row] = [r for r in tables(section(GUIDE, 2, "Talking to Jira")) [0][1:] if r[0] == action]
    assert form in row[1] and row[2], row


def jira_row(action: str) -> list[str]:
    [row] = [r for r in tables(section(GUIDE, 2, "Talking to Jira"))[0][1:] if r[0] == action]
    return row


def test_no_request_uses_version_2_of_jira_s_interface():
    # Version 2 reads text as wiki markup, which re-renders Markdown.
    assert "/rest/api/2/" not in GUIDE


@pytest.mark.parametrize("action, built", [("Create a ticket", "description: adf($d)"),
                                           ("Post a comment", "{body: adf($b)}")])
def test_text_is_sent_as_a_document(action, built):
    row = jira_row(action)
    assert '"$ADF"' in row[1] and built in row[1], row


def test_the_document_builder_has_text_documents_shape():
    text = section(GUIDE, 2, "Talking to Jira")
    [block] = [b for b in fenced(text) if b.startswith("```sh\nADF='")]
    assert '{type: "doc", version: 1, content: .}' in block
    assert '{type: "hardBreak"}, {type: "text", text: .}' in block
    assert "def adf_text(d):" in block


def test_reading_a_ticket_names_the_custom_fields():
    row = jira_row("Read one ticket")
    assert "<project field>,<item field>,<effort field>,<complexity field>" in row[1]


def test_the_issue_type_is_the_configured_one():
    row = jira_row("Create a ticket")
    assert 'issuetype: {name: $t}' in row[1] and '"Task"' not in row[1]
    assert "TYPE=Task                                     # work.jira.issue-type" in \
        section(GUIDE, 2, "Talking to Jira")


def test_jira_credentials_are_read_from_the_variables_the_configuration_names():
    text = section(GUIDE, 2, "Talking to Jira")
    assert 'AUTH="$(printenv "$EMAIL_ENV"):$(printenv "$TOKEN_ENV")"' in text
    assert "TOKEN_ENV=TCW_JIRA_API_KEY" in text and "TCW_JIRA_TOKEN" not in GUIDE


def test_the_create_search_starts_the_day_before_the_start_date():
    assert 'created >= "<the day before the start date>"' in section(GUIDE, 2, "Rules")


def test_every_request_file_already_in_the_description_is_deleted_unposted():
    text = " ".join(section(GUIDE, 3, "The request").split())
    assert "`intake.md` or `initial-request.md` alike" in text
    assert "deleted without asking and without posting anything" in text


def test_a_2x_import_of_the_ticket_counts_as_contained_without_comparing():
    # 2.x wrote an imported intake from the description in wiki markup, so a
    # text comparison with the description read back as a document never
    # matches (2.x tcw/work/cli.py, `_intake_text`).
    text = " ".join(section(GUIDE, 3, "The request").split())
    assert "**a 2.x import of this ticket**" in text
    assert "`Imported on <date> from [<KEY>](https://…/browse/<KEY>) (jira-cloud).` with this ticket's own key" \
        in text
    assert "it is not compared" in text
    [block] = [b for b in fenced(section(GUIDE, 2, "Talking to Jira"))
               if "--rawfile r" in b]
    assert '[ "$(basename "$F")" = intake.md ]' in block
    assert 'grep -qE "^Imported on [^ ]+ from \\[$T\\]\\(" "$F"' in block
    # The text comparison no longer drops the line, so it cannot hide one.
    assert "Imported on" not in block[block.index("jq -r"):]
    # The import is trusted only while the file, uncommitted changes included,
    # is byte for byte what 2.x's import commit added: commit statuses cannot
    # show an edit made in the same commit as a move, or one never committed.
    assert 'C=$(git log -1 --format=%H --grep="^tcw work: import $T " 2>/dev/null)' in block
    assert 'git show "$C:$P" | cmp -s - "$F"' in block
    assert "diff-filter=M" not in block
    assert "an edited import, or one with no import commit, is compared like any other file" in text


def test_step_2_says_what_step_3_checks_and_lists_the_rest():
    text = " ".join(step(2).split())
    assert "the configured one (`work.jira.issue-type`, `Task` by default) and the " \
           "project's sub-task type" in text
    assert "reporting `unchecked:` for that edit screen otherwise" in text
    assert "It never reads an epic's screens or workflow" in text
    assert "one line per type for its create screen, its edit screen" in text
    assert "checks each of these at step 3" not in text
    assert '"$SITE/rest/api/3/issue/createmeta/$KEY/issuetypes/<type id>?startAt=0&maxResults=200"' \
        in jira_row("Read a create screen")[1]
    assert "repeat with `startAt` moved on" in jira_row("Read a create screen")[1]
    assert '"$SITE/rest/api/3/issue/$KEY-42/editmeta"' in jira_row("Read an edit screen")[1]


def test_the_reader_writes_the_text_files_requests_read():
    text = " ".join(section(GUIDE, 2, "Talking to Jira").split())
    assert "write the text there yourself, the description to `$J/request.md` and a " \
           "comment, fixed first line included, to `$J/comment.txt`" in text


def test_a_failing_step_12_check_keeps_its_output_out_of_the_log():
    text = " ".join(check(12).split())
    assert "**When the check fails, its output quotes the lines that differ, private " \
           "ones included**" in text
    assert "record in the log only the files it names" in text
    assert "for step 12's check when it fails, only what step 12 says" in \
        " ".join(section(GUIDE, 2, "Rules").split())


def test_step_6_finds_a_ticket_without_tracker_yaml():
    text = step(6)
    assert "`ticket.key` in its `tracker.yaml`" in text
    assert "the `ticket:` line of its `item.yaml`" in text
    assert "the key at the front of its folder's name" in text
    assert "<KEY>-[1-9][0-9]*-[a-z0-9]+(-[a-z0-9]+)*" in check(6)


# -- Criterion 32: step 12 revisits agent instructions and memories ---------------------

def step_12() -> str:
    return step(12)


def fenced(text: str) -> list[str]:
    return FENCE.findall(text)


# Each place criterion 32 lists, as the prose names it (a folder with its
# trailing `/`). The fenced list of places names each one without the `/`.
PLACES = (
    "CLAUDE.md", "AGENTS.md", ".claude/skills/", ".claude/commands/", ".claude/agents/",
    ".codex/", ".agents/skills/", ".claude/settings.json", ".claude/settings.local.json",
    "~/.claude/CLAUDE.md", "~/.codex/AGENTS.md", "~/.claude/skills/", "~/.claude/commands/",
    "~/.claude/agents/", "~/.codex/skills/", "~/.agents/skills/", "~/.codex/prompts/",
    "~/.claude/settings.json", "~/.codex/rules/", "~/.codex/memories/",
)


def places_block() -> str:
    [block] = [b for b in fenced(step_12()) if "PLACES=()" in b]
    return block


@pytest.mark.parametrize("place", PLACES)
def test_step_12_names_each_place(place):
    assert f"`{place}`" in step_12(), f"step 12's list does not name `{place}`"
    assert re.search(rf"(?<![\w./~-]){re.escape(place.rstrip('/'))}(?![\w./-])",
                     places_block()), f"step 12's places command leaves out {place}"


def test_step_12_finds_memory_folders_by_what_their_records_say():
    text = step_12()
    assert "`git worktree list --porcelain`" in text and "`MEMORY.md`" in text
    block = places_block()
    assert "find ~/.claude/projects -mindepth 2 -maxdepth 2 -name '*.jsonl'" in block
    assert '-e "\\"cwd\\":\\"$path\\"" -e "\\"cwd\\":\\"$path/"' in block


def test_step_12_searches_the_primary_checkouts_own_files_from_a_worktree():
    text = step_12()
    assert "**A run made in a worktree** also searches the primary checkout's untracked\n" \
           "per-user files" in text
    assert "`git -C <primary checkout> status --ignored --porcelain -- .claude .codex`" in text
    assert 'git -C "$PRIMARY" status --ignored --porcelain -- .claude .codex' in places_block()


@pytest.mark.parametrize("action", ["**delete**", "**rewrite**", "**keep**"])
def test_step_12_proposes_delete_rewrite_or_keep(action):
    assert action in step_12()


def test_step_12_reads_every_file_the_broad_search_prints_in_full():
    text = step_12()
    search = 'grep -rlsE "\\btcw\\b|(^|[^[:alnum:]_])($NAMES)|\\b($WORDS)\\b" "${PLACES[@]}"'
    assert any(search in b for b in fenced(text))
    after = text[text.index(search):]
    assert after.index("**Read each printed file in full**") < after.index("**Stop and ask**")


def test_step_12s_check_compares_the_names_search_with_the_logs_expected_lines():
    text = check(12)
    assert "`grep -c '^## Agent instructions' <log>` prints `1`" in text
    [block] = [b for b in fenced(text) if b.startswith("```sh\ndiff ")]
    assert 'grep -rIsHE "(^|[^[:alnum:]_])($NAMES)" "${PLACES[@]}" | LC_ALL=C sort' in block
    assert "/^```expected-names$/" in block
    assert 'cat "$PRIVATE"' in block


def test_step_12_keeps_text_from_outside_the_repository_out_of_the_log():
    text = " ".join(step_12().split())
    assert "**Nothing private goes into the log.**" in text
    assert "never the passage" in text
    assert "outside the repository and never committed" in text


def alternatives(name: str) -> str:
    [line] = [l for b in fenced(step_12()) for l in b.splitlines()
              if l.startswith(f"{name}='")]
    return line[len(name) + 2:-1]


def coverage() -> re.Pattern:
    return re.compile(rf"(?:^|[^A-Za-z0-9_])(?:{alternatives('NAMES')})"
                      rf"|\b(?:{alternatives('WORDS')})\b")


def _top_level(pattern: str) -> list[str]:
    """`pattern`'s alternatives, split at each `|` outside parentheses."""
    out, depth, current = [], 0, ""
    for char in pattern:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "|" and depth == 0:
            out.append(current)
            current = ""
        else:
            current += char
    return out + [current]


def _names_match(names: str, text: str) -> bool:
    return bool(re.search(rf"(?:^|[^A-Za-z0-9_])(?:{names})", text))


# 2.x text the first columns do not name, each checked in 2.8.x's source, with
# the start of the one alternative of NAMES that finds it: each text is found
# by that alternative alone, so removing it turns this red.
@pytest.mark.parametrize("text, alternative", [
    ("run it with --worktree", "--worktree"),
    ("the Definition of Done", "Definition of Done"),
    ("a tracker sync failed", "tracker sync"),
    ("transitions.claim", r"transitions\."),
    ("transitions.start", r"transitions\."),
])
def test_names_finds_2x_text_outside_the_tables(text, alternative):
    finding = [a for a in _top_level(alternatives("NAMES")) if _names_match(a, text)]
    assert len(finding) == 1 and finding[0].startswith(alternative), (text, finding)


def test_names_holds_no_bare_tcw():
    assert "tcw" not in re.split(r"[|()]", alternatives("NAMES"))


STATUS_FOLDERS = ("inbox", "backlog", "active", "review", "blocked", "completed", "discarded")


@pytest.mark.parametrize("folder", STATUS_FOLDERS)
def test_names_holds_each_status_folder_with_its_trailing_slash_only(folder):
    forms = [a for a in alternatives("NAMES").split("|") if folder in a and "/" in a]
    assert forms == [f"{folder}/"], forms


# First-column spans the searches deliberately do not match, each with its
# reason. Three reasons cover them all.
_KEPT = "kept in 3.0 with the same meaning, so a mention of it is not a finding"
_GENERIC = ("a common word, found through the file's other names (`state.yaml`, "
            "`tracker.yaml`, `tcw`), after which the whole file is read")
_ARGUMENTS = ("a 3.0 command whose 2.x arguments or flags changed; every file naming "
              "`tcw` is read in full, which is where an old argument form is found")
STEP_12_EXCEPTIONS = {
    **dict.fromkeys((
        "title", "priority", "effort", "complexity", "tags", "parent", "ticket",
        "capabilities.yaml", "skill", "pre", "post", "when:", "generate", "email-env",
        "token-env", "discard", "work.tags", "work.documentation", "work.path",
        "work.repository", "work.procedures.<id>", "TCW_ITEM_PATH", "TCW_HOOK_ROLE",
        "TCW_HOOK_KIND", "TCW_HOOK_ID", "TCW_HOOK_PHASE", "AGENTS.md", "CLAUDE.md",
        ".gitignore", "tcw --version", "tcw serve", "tcw init", "tcw taxonomy list",
        "tcw taxonomy show", "tcw taxonomy search", "tcw taxonomy path", "tcw taxonomy rm",
        "tcw taxonomy extends add", "tcw taxonomy extends rm", "tcw capabilities show",
        "tcw capabilities search", "tcw capabilities path", "tcw capabilities set",
        "tcw capabilities reset", "tcw capabilities rm", "tcw capabilities drift",
        "tcw work show <slug> [--json]", "tcw work path [<slug>]", "tcw work docs",
        "tcw work stage prompt <stage> [<slug>] [--no-exec]", "tcw work tags list|add|rm",
    ), _KEPT),
    **dict.fromkeys((
        "slug", "created", "owner", "type", "started", "completed", "phase", "branch",
        "schema", "provider", "project", "part", "bound", "comment", "owed", ".md",
        ".gitkeep",
    ), _GENERIC),
    **dict.fromkeys((
        "tcw validate <path>", "tcw taxonomy <path>", "tcw capabilities <path>",
        "tcw taxonomy add <name> <description>", "-s", "-p",
        "tcw capabilities add <path> <name> -s <status>", "tcw capabilities extends <id>",
        "tcw capabilities extends <id> --rm", "tcw work stage <stage> <slug>",
        "tcw work list -i", "tcw work edit <slug> --type", "--priority",
        "tcw work rename <slug> <new-slug>",
        "tcw work lifecycle <slug> --directive --phase --transition",
    ), _ARGUMENTS),
    "tcw://work/<old slug>": "found by step 9's search for the renamed folders' old names",
}


def test_every_first_column_name_is_found_by_step_12s_searches():
    pattern = coverage()
    missed = sorted({s for s in first_column_spans()
                     if s not in STEP_12_EXCEPTIONS and not pattern.search(s)})
    assert not missed, "step 12's NAMES and WORDS miss: " + ", ".join(missed)


def test_every_exception_is_a_first_column_name_the_searches_miss():
    spans, pattern = set(first_column_spans()), coverage()
    stale = sorted(s for s in STEP_12_EXCEPTIONS if s not in spans or pattern.search(s))
    assert not stale, stale


# -- Criterion 10, its automatic part: every 3.0 command named parses --------------------

from tests.test_documented_cli_surface import _check, _invocations, tree  # noqa: E402,F401

# 2.x commands this guide names outside a mapping table's first column, each
# with the reason it is named there.
TWO_X_SPANS: dict[str, str] = {}


def _without_first_cells(text: str) -> str:
    """The guide with each table row's first cell emptied: that column names 2.x
    commands on purpose."""
    return "\n".join(re.sub(r"^\|(\\\||[^|])*\|", "| |", line) if line.startswith("|") else line
                     for line in text.splitlines())


def test_every_command_outside_a_first_column_parses_on_3_0(tree):
    problems = []
    for span in _invocations(_without_first_cells(GUIDE)):
        if span in TWO_X_SPANS:
            continue
        if (problem := _check(span, tree)) is not None:
            problems.append(f"`{span}`: {problem}")
    assert not problems, "\n  ".join(["the guide names commands 3.0 lacks:", *problems])
