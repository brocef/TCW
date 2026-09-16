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

# Where each default was copied from. Written out, not derived. Until a source
# is converted, this is what stops the shipped default and the source drifting
# apart. A converted source keeps its row, wrapped in `Composes`, and is checked
# instead for reading the procedure and for carrying no copy of its default.


class Composes(str):
    """A source that reads its default through `tcw work procedure prompt`
    instead of carrying a copy of it. A skill must inject the command and name
    it in its manual fallback; a reference document, where nothing is injected,
    must name it. Either way no paragraph of the default may survive in it."""


SOURCES = {
    "unattended-work": Composes("skills/tcw-extras-autonomous-work/SKILL.md"),
    "triage-issues": Composes("skills/tcw-extras-triage-issues/SKILL.md"),
    "documentation-sync": "skills/documentation-sync/SKILL.md",
    "post-mortem": Composes("skills/tcw-post-mortem/SKILL.md"),
    "create-work": "skills/tcw-work-create/SKILL.md",
    "audit-backlog": Composes("skills/tcw-work/references/procedures/audit-backlog.md"),
    "consolidate-plans": Composes("skills/tcw-work/references/procedures/consolidate-plans.md"),
    "decompose": Composes("skills/tcw-work/references/procedures/decompose.md"),
    "delegation": Composes("skills/tcw-work/references/procedures/delegation.md"),
    "search": Composes("skills/tcw-work/references/procedures/search.md"),
}

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


def _copied_paragraphs(default: str, text: str) -> list[str]:
    """Paragraphs of `default` that also appear, reflowed or not, in `text`."""
    return sorted(_paragraphs(default) & _paragraphs(text))


@pytest.mark.parametrize("pid", PROCEDURE_IDS)
def test_each_default_is_todays_text(pid):
    """Criterion 2: a project that configures nothing gets today's words.

    A converted source reads its default through `tcw work procedure prompt
    <id>` instead of copying it, so the two are no longer equal by design.
    There the drift to catch is a paragraph left in both places, which a
    project's replacement would not remove."""
    source = SOURCES[pid]
    text = (REPO / source).read_text(encoding="utf-8")
    default = load_builtins().procedures[pid]
    if isinstance(source, Composes):
        command = f"tcw work procedure prompt {pid}"
        if source.endswith("SKILL.md"):
            assert f"!`{command}" in text, f"{source} does not inject `{command}`"
            _, _, summary = text.partition("## Document command summary")
            assert command in summary, f"{source} has no manual fallback naming the command"
        else:
            assert command in text, f"{source} does not point the reader at `{command}`"
        copied = _copied_paragraphs(default, text)
        assert not copied, (f"{source} still carries text from "
                            f"tcw/work/procedures/{pid}.md: {copied[0][:80]!r}")
        return
    expected = _body(REPO / source).strip()
    assert expected, f"{source} has no body to compare"
    assert default.strip() == expected, \
        f"tcw/work/procedures/{pid}.md differs from {source}"


def test_the_post_mortem_agent_reads_the_procedure():
    """The agent restates the skill; once the skill's text can be replaced, a
    copy in the agent would silently skip a project's replacement."""
    text = (REPO / "agents/tcw-post-mortem.md").read_text(encoding="utf-8")
    assert "tcw work procedure prompt post-mortem" in text
    copied = _copied_paragraphs(load_builtins().procedures["post-mortem"], text)
    assert not copied, f"agents/tcw-post-mortem.md carries the default: {copied[:1]}"


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

