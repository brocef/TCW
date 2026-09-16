"""The procedure texts TCW ships, and the packaging that carries them.

Mirrors `test_shipped_prompts.py` for `tcw/work/procedures/`. Everything goes
through `load_builtins()`, so the assertions hold in an installed tree too.
"""

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
    "audit-backlog": "skills/tcw-work/references/procedures/audit-backlog.md",
    "consolidate-plans": "skills/tcw-work/references/procedures/consolidate-plans.md",
    "decompose": "skills/tcw-work/references/procedures/decompose.md",
    "delegation": "skills/tcw-work/references/procedures/delegation.md",
    "search": "skills/tcw-work/references/procedures/search.md",
}

# Skills that no longer carry a copy of their default: the fixed part stays in
# the skill, the rest is read from `tcw work procedure prompt <id>`. There is no
# second copy to drift from, so these are checked for the reading instead.
CONVERTED = {
    "create-work": "skills/tcw-work-create/SKILL.md",
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
    assert not set(SOURCES) & set(CONVERTED)
    assert set(SOURCES) | set(CONVERTED) == set(PROCEDURE_IDS)


@pytest.mark.parametrize("pid", sorted(CONVERTED))
def test_a_converted_skill_reads_its_procedure(pid):
    """Epic criterion 11: the skill injects its procedure and names the command
    for a harness that runs no injection, and holds no copy of the default."""
    body = _body(REPO / CONVERTED[pid])
    command = f"tcw work procedure prompt {pid}"
    assert f"!`{command}" in body, f"{CONVERTED[pid]} does not inject {command}"
    _, _, summary = body.partition("## Document command summary")
    assert command in summary.split("```", 2)[1], \
        f"{CONVERTED[pid]} has no fallback block naming {command}"
    first = next(line for line in load_builtins().procedures[pid].splitlines()
                 if line.strip() and not line.startswith("#"))
    assert first not in body, f"{CONVERTED[pid]} still carries its default"


@pytest.mark.parametrize("pid", sorted(SOURCES))
def test_each_default_is_todays_text(pid):
    """Criterion 2: a project that configures nothing gets today's words."""
    expected = _body(REPO / SOURCES[pid]).strip()
    assert expected, f"{SOURCES[pid]} has no body to compare"
    assert load_builtins().procedures[pid].strip() == expected, \
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

