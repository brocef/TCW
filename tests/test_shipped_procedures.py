"""The procedure texts TCW ships, and the packaging that carries them.

Mirrors `test_shipped_prompts.py` for `tcw/work/procedures/`. Everything goes
through `load_builtins()`, so the assertions hold in an installed tree too.
Each procedure is one file and nothing else (TCW-74 Design 5.2): no second
half under a skill's references, so there is no source map to keep in step.
"""

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

