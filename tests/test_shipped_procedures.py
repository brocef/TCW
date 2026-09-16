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
# apart. Once it reads `tcw work procedure prompt <id>` its row stays, and
# `test_each_default_is_todays_text` checks instead that no paragraph of the
# default is left behind in it.
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


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 40]


@pytest.mark.parametrize("pid", PROCEDURE_IDS)
def test_each_default_is_todays_text(pid):
    """Criterion 2: a project that configures nothing gets today's words.

    A converted source reads its default through `tcw work procedure prompt
    <id>` instead of copying it, so the two are no longer equal by design.
    There the drift to catch is a paragraph left in both places, which a
    project's replacement would not remove."""
    source = _body(REPO / SOURCES[pid])
    default = load_builtins().procedures[pid]
    assert source.strip(), f"{SOURCES[pid]} has no body to compare"
    if f"tcw work procedure prompt {pid}" in source:
        left = [p for p in _paragraphs(default) if p in source]
        assert not left, (f"{SOURCES[pid]} still carries text from "
                          f"tcw/work/procedures/{pid}.md: {left[0][:80]!r}")
        return
    assert default.strip() == source.strip(), \
        f"tcw/work/procedures/{pid}.md differs from {SOURCES[pid]}"


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

