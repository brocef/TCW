"""The procedure texts TCW ships, and the packaging that carries them.

Mirrors `test_shipped_prompts.py` for `tcw/work/procedures/`. Everything goes
through `load_builtins()`, so the assertions hold in an installed tree too.
Each procedure is one file and nothing else (TCW-74 Design 5.2): no second
half under a skill's references, so there is no source map to keep in step.
"""

import re
from importlib.resources import files
from pathlib import Path

import pytest

from tcw.store.base import PROCEDURE_IDS
from tcw.work.resolve import ResolveError, load_builtins

REPO = Path(__file__).resolve().parent.parent

# TCW-74 Design 5.1, written out rather than derived, so a change to the set is
# a deliberate edit here as well as in `PROCEDURE_IDS`.
EXPECTED = {"documentation-sync", "create-work", "audit-backlog", "search",
            "triage-issues", "unattended-work", "pause-work"}


def test_the_procedure_set_is_exactly_the_design():
    """Criterion 6: the loaded procedures are exactly these seven."""
    assert set(PROCEDURE_IDS) == EXPECTED
    assert set(load_builtins().procedures) == EXPECTED


def test_each_procedure_is_one_file_in_the_package():
    """Criterion 6: one file per id in the packaged folder, and nothing else."""
    folder = files("tcw.work") / "procedures"
    present = {entry.name for entry in folder.iterdir()
               if entry.name.endswith(".md")}
    assert present == {f"{pid}.md" for pid in EXPECTED}


def test_no_procedure_has_a_second_half_under_a_skill():
    """Criterion 6: the split halves under the work skill are gone."""
    assert not (REPO / "skills" / "work" / "references" / "procedures").exists()


def _paragraphs(text: str) -> set[str]:
    """Blank-line-separated blocks, whitespace-normalized; headings and short
    fragments are not evidence of a copy."""
    blocks = (" ".join(b.split()) for b in re.split(r"\n\s*\n", text))
    return {b for b in blocks if len(b) >= 40 and not b.startswith("#")}


def test_the_backlog_auditor_reads_the_procedure():
    """The agent is dispatched per item by the audit procedure. A copy of the
    checks in it would audit against TCW's list after a project replaced it."""
    text = (REPO / "agents/backlog-auditor.md").read_text(encoding="utf-8")
    assert "tcw work procedure audit-backlog" in text
    assert "procedure prompt" not in text
    tools = next(line for line in text.splitlines() if line.startswith("tools:"))
    assert "Bash" in tools, "the agent cannot run the command without Bash"
    default = load_builtins().procedures["audit-backlog"]
    copied = sorted(_paragraphs(default) & _paragraphs(text))
    assert not copied, f"agents/backlog-auditor.md carries the default: {copied[:1]}"
    named = [c for c in ("Already done", "Outdated", "Wrong project",
                         "Unactionable", "Blocked with no next action",
                         "Capability drift") if c.lower() in text.lower()]
    assert not named, f"agents/backlog-auditor.md still names: {named}"


def test_the_reviewer_reads_the_review_stage():
    """TCW-74 choice 9: the reviewer carries no review steps of its own, so a
    project's review prompt reaches it."""
    text = (REPO / "agents/reviewer.md").read_text(encoding="utf-8")
    assert "name: reviewer" in text
    assert "tcw work stage prompt review <slug>" in text
    default = load_builtins().stage_prompts["review"]
    copied = sorted(_paragraphs(default) & _paragraphs(text))
    assert not copied, f"agents/reviewer.md carries the review prompt: {copied[:1]}"
    assert not (REPO / "agents/verifier.md").exists()
    assert not (REPO / "agents/post-mortem.md").exists()


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



# -- TCW-113 Design 7.1, AC 37: the audit covers the family ---------------------------


def test_ac37_the_audit_starts_from_the_family_and_names_items_in_full():
    text = load_builtins().procedures["audit-backlog"]
    for wanted in ("tcw work list --scope down --json", "unavailable",
                   "tcw work list --scope down --all --json",
                   "tcw work show <full-id>"):
        assert wanted in text, wanted
    flat = " ".join(text.split())
    assert not re.search(r"Start with `tcw work list`", flat)
    assert not re.search(r"`tcw work list`(?! --)", flat)
    for stale in ("tcw work show <slug>", "tcw work path <slug>",
                  "tcw work discard <slug>"):
        assert stale not in flat, stale


def test_ac37_the_auditor_is_given_an_item_by_its_full_identifier():
    text = (REPO / "agents/backlog-auditor.md").read_text(encoding="utf-8")
    given = text.split("## What you are given", 1)[1].split("\n## ", 1)[0]
    assert "full identifier" in given
    assert "tcw work show <slug>" not in text
    assert "tcw work show <full-id>" in text
