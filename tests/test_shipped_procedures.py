"""The procedure texts TCW ships, and the packaging that carries them.

Mirrors `test_shipped_prompts.py` for `tcw/work/procedures/`. Everything goes
through `load_builtins()`, so the assertions hold in an installed tree too.
"""

import re
from pathlib import Path

import pytest

from tcw.store.base import PROCEDURE_IDS
from tcw.work.resolve import ResolveError, load_builtins

REPO = Path(__file__).resolve().parent.parent

# Where each default was copied from. Written out, not derived: a conversion
# child that turns one of these skills into a reader of
# `tcw work procedure prompt` changes both sides on purpose, and changes or
# removes its row here in the same commit. Until then this is what stops the
# shipped default and the skill drifting apart.
SOURCES = {
    "unattended-work": "skills/tcw-extras-autonomous-work/SKILL.md",
    "triage-issues": "skills/tcw-extras-triage-issues/SKILL.md",
    "documentation-sync": "skills/documentation-sync/SKILL.md",
    "post-mortem": "skills/tcw-post-mortem/SKILL.md",
    "create-work": "skills/tcw-work-create/SKILL.md",
    "audit-backlog": "skills/tcw-work/references/procedures/audit-backlog.md",
    "consolidate-plans": "skills/tcw-work/references/procedures/consolidate-plans.md",
    "decompose": "skills/tcw-work/references/procedures/decompose.md",
    "delegation": "skills/tcw-work/references/procedures/delegation.md",
    "search": "skills/tcw-work/references/procedures/search.md",
}

# Ids whose source no longer carries a copy: it tells its reader to run
# `tcw work procedure prompt <id>` and keeps only the rules a project's text
# must not be able to remove. For these, the check turns around — the source
# names the command and shares no paragraph with the default, so neither a
# pasted-back copy nor a fixed rule leaking into the default passes.
CONVERTED: set[str] = {"delegation", "audit-backlog", "consolidate-plans", "decompose",
                         "search"}


def _body(path: Path) -> str:
    """A skill's text after its YAML frontmatter; a reference document whole."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        text = text[text.index("\n---\n", 3) + len("\n---\n"):]
    return text


def test_every_procedure_ships_a_default():
    assert set(load_builtins().procedures) == set(PROCEDURE_IDS)


def test_the_source_map_covers_exactly_the_ids():
    assert set(SOURCES) == set(PROCEDURE_IDS)


def _paragraphs(text: str) -> set[str]:
    """Blank-line-separated blocks, whitespace-normalized; headings and short
    fragments are not evidence of a copy."""
    blocks = (" ".join(b.split()) for b in re.split(r"\n\s*\n", text))
    return {b for b in blocks if len(b) >= 40 and not b.startswith("#")}


@pytest.mark.parametrize("pid", PROCEDURE_IDS)
def test_each_default_is_todays_text(pid):
    """Criterion 2: a project that configures nothing gets today's words."""
    if pid in CONVERTED:
        source = _body(REPO / SOURCES[pid])
        assert f"tcw work procedure prompt {pid}" in source, \
            f"{SOURCES[pid]} does not send its reader to the command"
        shared = _paragraphs(source) & _paragraphs(load_builtins().procedures[pid])
        assert not shared, \
            f"{SOURCES[pid]} and tcw/work/procedures/{pid}.md share: {sorted(shared)}"
        return
    expected = _body(REPO / SOURCES[pid]).strip()
    assert expected, f"{SOURCES[pid]} has no body to compare"
    assert load_builtins().procedures[pid].strip() == expected, \
        f"tcw/work/procedures/{pid}.md differs from {SOURCES[pid]}"


def test_the_backlog_auditor_reads_the_procedure():
    """The agent is dispatched per item by the audit procedure. A copy of the
    checks in it would audit against TCW's list after a project replaced it."""
    text = (REPO / "agents/tcw-backlog-auditor.md").read_text(encoding="utf-8")
    assert "tcw work procedure prompt audit-backlog" in text
    tools = next(line for line in text.splitlines() if line.startswith("tools:"))
    assert "Bash" in tools, "the agent cannot run the command without Bash"
    copied = [c for c in ("Already completed", "Outdated", "Wrong repository",
                          "Unactionable", "Blocked without a next action",
                          "Capability drift") if c.lower() in text.lower()]
    assert not copied, f"agents/tcw-backlog-auditor.md still names: {copied}"


def _fail_procedures(monkeypatch, error):
    """Make only the procedure files unreadable, so stage prompts loading first
    cannot be what raises."""
    import tcw.work.resolve as resolve
    real = resolve.files

    class _Root:
        def __init__(self, inner):
            self.inner = inner

        def __truediv__(self, part):
            if str(part).startswith("procedures/"):
                return _Bad()
            return self.inner / part

    class _Bad:
        def read_text(self, **_kw):
            return error()

    monkeypatch.setattr(resolve, "files", lambda pkg: _Root(real(pkg)))
    resolve.load_builtins.cache_clear()


def _raising():
    raise FileNotFoundError


@pytest.mark.parametrize("make, word", [(_raising, "missing"), (lambda: "  \n", "empty")])
def test_a_missing_or_empty_default_is_a_loud_failure(monkeypatch, make, word):
    """Criterion 9."""
    import tcw.work.resolve as resolve
    _fail_procedures(monkeypatch, make)
    try:
        with pytest.raises(ResolveError) as e:
            resolve.load_builtins()
    finally:
        monkeypatch.undo()
        resolve.load_builtins.cache_clear()
    message = str(e.value)
    first = sorted(PROCEDURE_IDS)[0]
    assert f"procedure '{first}'" in message and word in message
    assert "tcw/work/procedures" in message
    assert "stage" not in message

