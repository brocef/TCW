"""The text TCW ships to agents: no git, no 2.x vocabulary, only commands that
exist, and exactly the documents TCW-74 decided to keep (TCW-74 spec,
Design 6, 7 and 10; acceptance criteria 7 to 10).

"Shipped text" is every Markdown file under `skills/`, `agents/`,
`tcw/work/prompts/` and `tcw/work/procedures/`. One file walk serves every scan
here, so they cannot disagree about what is scanned. Each scan's exceptions are
a named constant with a reason per entry, so a reviewer sees every one.
"""

import argparse
import json
import re
from pathlib import Path

import pytest

from tcw.cli import build_parser
from tcw.store.base import PROCEDURE_IDS
from tcw.work.layout import front_matter
from tcw.work.model import STAGES
from tests.doc_allowance import (REFUSED_KEYS, REFUSED_VALUES, REMOVED_COMMANDS,
                                  REMOVED_FLAGS, REMOVED_FORMS)
from tests.doc_vocabulary import PATTERNS, scan
from tests.test_documented_cli_surface import (DOC_FILES, INVOCATION, KEY_SPELLING,
                                               TOP_KEY_SPELLING, _invocations)

REPO = Path(__file__).resolve().parent.parent

# The release flow keeps its commit and tag steps (TCW-74 spec, Non-goals); the
# git scan only, never the vocabulary scan, exempts it.
GIT_EXEMPT = ("skills/documentation-sync/", "tcw/work/procedures/documentation-sync.md")

GIT_WORDS = re.compile(
    r"\b(git|commits?|committed|committing|push\w*|pull\w*|worktrees?|trunk|branch\w*)\b",
    re.IGNORECASE)

# Exact phrases the git scan accepts, each a fact rather than an instruction.
GIT_ALLOWED = {
    "skills/extras-report/SKILL.md": {
        "repository, branch and directory names":
            "advice on anonymizing an example in a bug report, not on running git "
            "(TCW-74 Design 6.3)",
    },
    "skills/configure/references/personal.md": {
        "git worktree of the project":
            "a fact: a linked worktree has no copy of the untracked personal file "
            "(TCW-75 spec, Design 6; TCW-72 spec, Risks)",
    },
    "skills/configure/references/stores.md": {
        "opened from a linked worktree":
            "a fact: how a relative store path is read from a linked worktree "
            "(TCW-75 spec, Design 1.5)",
        "#example-keeping-git-in-step-with-each-stage-change-something-your-project-adds":
            "the anchor of the configuration guide's opt-in example, which a "
            "project adds itself (TCW-75 spec, Design 6 and 8.2)",
    },
}

# TCW-74's own additions to the shared table: removals that TCW-75's documents
# may still show in command output (`builtin: true`), or that only the shipped
# text could name.
EXTRA_PATTERNS = (
    (r"builtin: true", "TCW-72 refuses `builtin:` in a file; write `inherit: true`"),
    (r"--owner\b", "removed flag; identity is `user.name`, `--assign-me` and `--mine` (TCW-72)"),
    (r"\bwork-stage\b", "deleted skill; stage text comes from `tcw work stage prompt` (TCW-74)"),
    (r"procedure prompt", "removed form; the command is `tcw work procedure <id>` (TCW-73)"),
    (r"\bplanning doc\b", "removed capability field (TCW-73)"),
)

# Exact phrases the vocabulary scan accepts, each with its reason.
VOCABULARY_ALLOWED: dict[str, dict[str, str]] = {
    "skills/configure/references/personal.md": {
        "- builtin: true  # built-in, tcw/work/prompts/spec.md":
            "`tcw config show` prints it for a built-in entry (review decision R8)",
    },
}

# What TCW-74's disposition table keeps, rewrites or adds (Design 7), and the
# `configure` skill, which TCW-75 rewrites (its Design 6).
SHIPPED = {
    "agents/backlog-auditor.md",
    "agents/reviewer.md",
    "skills/README.md",
    "skills/capabilities/SKILL.md",
    "skills/commands-drive-work-to-completion/SKILL.md",
    "skills/commands-pause-work/SKILL.md",
    "skills/commands-plan-work/SKILL.md",
    "skills/commands-process-inbox/SKILL.md",
    "skills/configure/SKILL.md",
    "skills/configure/references/docs-sync.md",
    "skills/configure/references/jira.md",
    "skills/configure/references/personal.md",
    "skills/configure/references/projects.md",
    "skills/configure/references/stores.md",
    "skills/configure/references/work.md",
    "skills/documentation-sync/SKILL.md",
    "skills/documentation-sync/references/cut-version.md",
    "skills/documentation-sync/references/release-notes-and-changelogs.md",
    "skills/documentation-sync/scripts/unpushed-version.sh",
    "skills/extras-autonomous-work/SKILL.md",
    "skills/extras-report/SKILL.md",
    "skills/extras-triage-issues/SKILL.md",
    "skills/setup/SKILL.md",
    "skills/setup/references/capabilities.md",
    "skills/setup/references/install.md",
    "skills/setup/references/jira.md",
    "skills/setup/references/project.md",
    "skills/setup/references/taxonomy.md",
    "skills/taxonomy/SKILL.md",
    "skills/work-create/SKILL.md",
    "skills/work-create/references/find-overlap.md",
    "skills/work/SKILL.md",
    "skills/work/references/commands.md",
    "skills/work/references/tags.md",
}

DELETED_SKILLS = ("commands-verify-work", "work-stage", "post-mortem")


def _rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _shipped_text() -> list[Path]:
    roots = ("skills", "agents", "tcw/work/prompts", "tcw/work/procedures")
    return sorted(p for root in roots for p in (REPO / root).rglob("*.md"))


OWNED = _shipped_text()
SKILL_FILES = sorted(p for p in OWNED if p.name == "SKILL.md")


def _allowed_at(line: str, start: int, end: int, phrases) -> bool:
    """Whether the match at [start, end) lies inside an allowed phrase."""
    for phrase in phrases:
        at = line.find(phrase)
        while at != -1:
            if at <= start and end <= at + len(phrase):
                return True
            at = line.find(phrase, at + 1)
    return False


def git_hits(rel: str, text: str) -> list[str]:
    phrases = GIT_ALLOWED.get(rel, {})
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        for m in GIT_WORDS.finditer(line):
            if not _allowed_at(line, m.start(), m.end(), phrases):
                out.append(f"{rel}:{number}: {m.group(0)!r}: {line.strip()}")
    return out


def vocabulary_hits(rel: str, text: str) -> list[str]:
    phrases = VOCABULARY_ALLOWED.get(rel, {})
    lines = text.splitlines()
    return [f"{rel}:{h.line}: {h.text!r} ({h.reason}): {lines[h.line - 1].strip()}"
            for h in scan(text, (*PATTERNS, *EXTRA_PATTERNS))
            if not _allowed_at(lines[h.line - 1], h.start, h.end, phrases)]


# ── criterion 8: no git, no 2.x vocabulary ───────────────────────────────────


def test_the_walk_sees_every_kind_of_shipped_text():
    rels = {_rel(p) for p in OWNED}
    assert "tcw/work/prompts/plan.md" in rels
    assert "tcw/work/procedures/pause-work.md" in rels
    assert "agents/reviewer.md" in rels
    assert "skills/work/references/commands.md" in rels
    assert "skills/configure/SKILL.md" in rels
    assert "skills/configure/references/personal.md" in rels


@pytest.mark.parametrize("doc", [p for p in OWNED if not _rel(p).startswith(GIT_EXEMPT)],
                         ids=_rel)
def test_no_shipped_text_names_git(doc):
    """Criterion 8: nothing tells an agent to run git, commit, push, pull,
    branch, use a worktree, or assumes the work is in git."""
    hits = git_hits(_rel(doc), doc.read_text(encoding="utf-8"))
    assert not hits, "git words in shipped text:\n  " + "\n  ".join(hits)


def test_every_git_allowance_is_still_needed():
    """An allowlist entry whose phrase has gone is an exception nobody needs."""
    for rel, phrases in GIT_ALLOWED.items():
        text = (REPO / rel).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, f"{rel} no longer says {phrase!r}; drop the entry"


AGENT_FILES = sorted(p for p in OWNED if _rel(p).startswith("agents/"))


def _granted_tools(doc: Path, key: str) -> list[str]:
    """Every tool a skill's `allowed-tools` or an agent's `tools` grants, read
    from parsed front matter, so a YAML list spread over several lines counts
    as much as a one-line comma-separated string."""
    meta = front_matter(doc.read_text(encoding="utf-8"))
    assert isinstance(meta, dict), f"{_rel(doc)} has no front matter"
    value = meta.get(key) or []
    if isinstance(value, str):
        value = value.split(",")
    return [str(tool).strip() for tool in value]


@pytest.mark.parametrize("skill", SKILL_FILES, ids=_rel)
def test_no_owned_skill_grants_git(skill):
    tools = _granted_tools(skill, "allowed-tools")
    assert not [t for t in tools if "git" in t.lower()], \
        f"{_rel(skill)} grants git: {tools}"


@pytest.mark.parametrize("agent", AGENT_FILES, ids=_rel)
def test_no_agent_grants_git(agent):
    tools = _granted_tools(agent, "tools")
    assert not [t for t in tools if "git" in t.lower()], \
        f"{_rel(agent)} grants git: {tools}"


def test_a_tool_list_over_several_lines_is_read_whole(tmp_path):
    """The grant scan reads parsed front matter, not the first line."""
    doc = tmp_path / "SKILL.md"
    doc.write_text("---\nname: x\nallowed-tools:\n  - Read\n  - Bash(git *)\n---\nbody\n")
    assert _granted_tools(doc, "allowed-tools") == ["Read", "Bash(git *)"]


@pytest.mark.parametrize("doc", OWNED, ids=_rel)
def test_no_shipped_text_uses_2x_vocabulary(doc):
    """Criterion 8: the shared table plus TCW-74's extra patterns, over every
    owned file, the documentation-sync files included."""
    hits = vocabulary_hits(_rel(doc), doc.read_text(encoding="utf-8"))
    assert not hits, "2.x vocabulary in shipped text:\n  " + "\n  ".join(hits)


def test_every_vocabulary_allowance_is_still_needed():
    for rel, phrases in VOCABULARY_ALLOWED.items():
        text = (REPO / rel).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, f"{rel} no longer says {phrase!r}; drop the entry"
            assert scan(phrase, (*PATTERNS, *EXTRA_PATTERNS)), \
                f"{phrase!r} matches no pattern; drop the entry"


@pytest.mark.parametrize("text, word", [
    ("Commit the plan.", "Commit"), ("push it", "push"), ("a worktree", "worktree"),
    ("on the trunk", "trunk"), ("run git log", "git"), ("pull request", "pull"),
])
def test_the_git_scan_sees_each_word(text, word):
    hits = git_hits("x.md", text)
    assert hits and repr(word) in hits[0]


@pytest.mark.parametrize("text", [
    "write `outcome.md`", "builtin: true", "tcw work start <slug>", "each node",
    "tcw work procedure prompt pause-work", "the Planning doc field",
])
def test_the_vocabulary_scan_sees_each_kind(text):
    assert vocabulary_hits("x.md", text)


@pytest.mark.parametrize("text", ["Node.js 22", "the item's folder", "documentation tasks"])
def test_the_vocabulary_scan_passes_plain_words(text):
    assert not vocabulary_hits("x.md", text)


# ── criterion 9: every command named exists ──────────────────────────────────

WORD = re.compile(r"[a-z][a-z0-9-]*$")
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z-]*")
PROMPT_STAGES = {s.name for s in STAGES if s.prompt}


def _children(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _placeholder(token: str) -> bool:
    return token.startswith(("<", "[<", '"<', "'<"))


def command_problem(span: str) -> str | None:
    """What is wrong with one documented `tcw …` invocation, or None."""
    tokens = span[INVOCATION.search(span).end():].split()
    parser, path = build_parser(), ["tcw"]
    rest = tokens
    for i, token in enumerate(tokens):
        children = _children(parser)
        if not children or not WORD.match(token):
            rest = tokens[i:]
            break
        if token not in children:
            return f"no such command: {' '.join([*path, token])}"
        parser, path = children[token], [*path, token]
    else:
        rest = []
    command = " ".join(path)
    first = rest[0] if rest else None
    if first is not None and not first.startswith("-") and not _placeholder(first):
        if command == "tcw work procedure" and first not in PROCEDURE_IDS:
            return f"no such procedure: {first}"
        if command == "tcw work stage prompt" and first not in PROMPT_STAGES:
            return f"no stage with a prompt: {first}"
    options = {o for a in parser._actions for o in a.option_strings}
    for flag in FLAG.findall(" ".join(rest)):
        if flag not in options:
            return f"no such flag: {flag} on {command}"
    return None


@pytest.mark.parametrize("doc", OWNED, ids=_rel)
def test_every_command_named_in_shipped_text_exists(doc):
    """Criterion 9: each `tcw …` command resolves in the 3.0 parser, flags
    included. The shared allowance list counts nowhere here."""
    rel = _rel(doc)
    problems = []
    for span in _invocations(doc.read_text(encoding="utf-8")):
        if (problem := command_problem(span)) is not None:
            problems.append(f"`{span}`: {problem}")
    assert not problems, f"{rel} names commands that do not exist:\n  " + \
        "\n  ".join(problems)


@pytest.mark.parametrize("span, problem", [
    ("tcw work start <slug>", "no such command: tcw work start"),
    ("tcw work procedure prompt pause-work", "no such procedure: prompt"),
    ("tcw work stage prompt verify <slug>", "no stage with a prompt: verify"),
    ("tcw work list --status active", "no such flag: --status on tcw work list"),
])
def test_the_command_check_sees_each_mistake(span, problem):
    assert command_problem(span) == problem


@pytest.mark.parametrize("span", [
    "tcw work procedure <id>", "tcw work procedure pause-work",
    "tcw work stage prompt review <slug>", "tcw work stage prompt <stage> <slug>",
    'tcw work new "<title>" --project <id>', "tcw work path <slug> qa --next",
    "tcw capabilities add <path> \"<Name>\" --status Supported",
])
def test_the_command_check_accepts_real_commands(span):
    assert command_problem(span) is None


def _names(text: str, entry: str) -> bool:
    """Whether the document `text` names the allowance entry `entry`: a
    command as an invocation, a key as a key."""
    if entry.startswith("tcw "):
        return any(" ".join(s[INVOCATION.search(s).start():].split()) == entry
                   or " ".join(s[INVOCATION.search(s).start():].split())
                   .startswith(entry + " ") for s in _invocations(text))
    keys = {f"work.{m.group(1)}" for m in KEY_SPELLING.finditer(text)}
    keys |= {m.group(0) for m in TOP_KEY_SPELLING.finditer(text)}
    return entry in keys


def _flag_named(text: str, command: str, flag: str) -> bool:
    """Whether the document `text` invokes `command` with `flag`."""
    for span in _invocations(text):
        words = " ".join(span[INVOCATION.search(span).start():].split())
        if words.startswith(command + " ") and flag in words.split():
            return True
    return False


ENTRIES = [*REMOVED_COMMANDS, *REMOVED_FORMS, *REFUSED_KEYS]


@pytest.mark.parametrize("entry", ENTRIES)
def test_no_allowance_entry_is_named_only_by_owned_text(entry):
    """Criterion 9: TCW-74 removes from the allowance list every entry only its
    own files named; one still named by an owned file fails the scans above
    anyway, so what this adds is that the list shrank."""
    owned = {_rel(p) for p in OWNED}
    namers = {_rel(d) for d in DOC_FILES if _names(d.read_text(encoding="utf-8"), entry)}
    assert not namers or not namers <= owned, \
        f"{entry} is named only by TCW-74's files ({sorted(namers)})"


@pytest.mark.parametrize("command, value", REFUSED_VALUES)
def test_no_allowance_value_is_named_only_by_owned_text(command, value):
    owned = {_rel(p) for p in OWNED}
    namers = {_rel(d) for d in DOC_FILES
              if _names(d.read_text(encoding="utf-8"), f"{command} {value}")}
    assert not namers or not namers <= owned, \
        f"{command} {value} is named only by TCW-74's files ({sorted(namers)})"


@pytest.mark.parametrize("command, flag", REMOVED_FLAGS)
def test_no_allowance_flag_is_named_only_by_owned_text(command, flag):
    owned = {_rel(p) for p in OWNED}
    namers = {_rel(d) for d in DOC_FILES
              if _flag_named(d.read_text(encoding="utf-8"), command, flag)}
    assert not namers or not namers <= owned, \
        f"{command} {flag} is named only by TCW-74's files ({sorted(namers)})"


# ── criterion 7: the documents match the disposition table ───────────────────


def test_the_shipped_files_are_exactly_the_disposition_table():
    found = {_rel(p) for root in ("skills", "agents") for p in (REPO / root).rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.name != ".DS_Store"}
    assert found == SHIPPED, (f"unexpected: {sorted(found - SHIPPED)}; "
                              f"missing: {sorted(SHIPPED - found)}")


INJECTION = re.compile(r"!`([^`]+)`")


@pytest.mark.parametrize("skill", sorted((REPO / "skills").glob("*/SKILL.md")), ids=_rel)
def test_every_injection_has_a_manual_fallback(skill):
    """Criterion 7: a harness that runs no injected command is told what to run."""
    text = skill.read_text(encoding="utf-8")
    commands = [c.removesuffix("|| true").strip() for c in INJECTION.findall(text)]
    if not commands:
        return
    _, found, summary = text.partition("## Document command summary")
    assert found, f"{_rel(skill)} injects {commands} with no Document command summary"
    for command in commands:
        assert command in summary, \
            f"{_rel(skill)}'s Document command summary does not name `{command}`"


def test_the_pause_skill_places_the_handoff_by_stage():
    """Criterion 7: the stage folder, a `Handoff` comment where the backend
    keeps the stage, and nothing at inbox."""
    text = (REPO / "skills/commands-pause-work/SKILL.md").read_text(encoding="utf-8")
    assert "--handoff" in text
    assert "`Handoff`" in text and "tcw work comment <slug>" in text
    inbox = [l for l in text.splitlines() if "inbox" in l]
    assert any("write nothing" in l.lower() for l in inbox), inbox
    assert "!`tcw work procedure pause-work" in text


def test_the_codex_manifest_names_no_deleted_skill():
    """Criterion 7, with the count checked in `test_plugin_manifests.py`."""
    manifest = json.loads((REPO / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    text = json.dumps(manifest)
    named = set(re.findall(r"`([a-z][a-z-]*)`", text))
    for skill in DELETED_SKILLS:
        assert skill not in named, f".codex-plugin/plugin.json names {skill}"
        assert not (REPO / "skills" / skill).exists()


# ── criterion 10: the capabilities skill reversal ────────────────────────────


def test_the_capabilities_skill_changes_records_with_the_code():
    text = (REPO / "skills/capabilities/SKILL.md").read_text(encoding="utf-8")
    for gone in ("--status Missing", "Planning doc", "tcw work complete",
                 "tcw work escalate", "ledger flip"):
        assert gone not in text, f"the capabilities skill still says {gone!r}"
    flat = " ".join(text.split())
    assert "same change as the code" in flat
    assert "No flipping at completion" in flat
    adds = [l for l in text.splitlines() if "tcw capabilities add" in l]
    assert adds
    assert all("--status" in l for l in adds), \
        [l for l in adds if "--status" not in l]
    assert any("--status Supported" in l for l in adds)
