"""The stage prompts TCW ships, and the packaging that carries them.

Everything here goes through `load_builtins()` rather than the source tree, so
the assertions hold in an installed tree as well as a checkout — and the wheel
case reads the built `.whl` itself, which is the only proof the files survive
packaging. Nothing here invokes `tcw work stage`: the registry is C3's library
and is tested as such.
"""

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tcw.store.base import STAGE_IDS
from tcw.work.resolve import load_builtins

SHIPPED = set(STAGE_IDS)
REPO = Path(__file__).resolve().parent.parent


def test_every_stage_ships_a_prompt():
    """The set is the derivation, never a hand-written list: a stage added to
    `STAGE_IDS` with no prompt file has to fail here.

    `inbox` is **in** the set. It runs before an item exists, which is why it
    long shipped nothing — but "no item to resolve against" was never a reason
    for TCW to have no instructions for it, only a reason for those
    instructions to take no work item reference.
    """
    assert set(load_builtins().stage_prompts) == SHIPPED
    assert "inbox" in load_builtins().stage_prompts


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_each_prompt_has_content(sid):
    text = load_builtins().stage_prompts[sid]
    assert text.strip()
    assert len([ln for ln in text.splitlines() if ln.strip()]) >= 15


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_each_prompt_stays_under_the_ceiling(sid):
    """50 lines, enforced rather than reviewed for — this is text an agent reads
    at every stage entry, and a ceiling that is only a convention erodes.

    Raised from 40 at C6's verify stage. Four of the six prompts landed at
    exactly 40, which is a ceiling with no margin: C7 moves clauses across the
    CLI/skill seam and could not accept one without first removing another,
    which would have let the ceiling decide the seam instead of the design.
    The guard is the point, not the number — it still refuses a prompt that
    grows back into the stage document it was condensed from.
    """
    assert len(load_builtins().stage_prompts[sid].splitlines()) <= 50


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_no_prompt_tells_the_agent_to_ask_what_it_is_reading(sid):
    """Step 1 of every source stage document — run `tcw work lifecycle --stage
    <id>` and honor what it reports — is circular inside the text that command
    reports, and is dropped."""
    assert "tcw work lifecycle --stage" not in load_builtins().stage_prompts[sid]


@pytest.mark.parametrize("sid", sorted(SHIPPED))
def test_no_prompt_names_a_sub_skill(sid):
    """The CLI states the obligation, the skill names the thing that discharges
    it — a skill name is a dangling reference for a user with no plugin."""
    text = load_builtins().stage_prompts[sid]
    for name in ("tcw-verifier", "documentation-sync", "tcw-capabilities"):
        assert name not in text


def test_the_self_review_pass_appears_in_exactly_three_prompts():
    """A pass earns its place only where it checks the artifact against a source
    outside itself — the tree, a prior artifact, a command's output. `request`
    has no such source, `verify` *is* the review pass, `postmortem` is terminal.

    Set equality rather than three presence checks: the failure this guards is a
    later editor copying the pass into all six, which turns a check into a
    ritual, and that direction is invisible to a presence check.
    """
    prompts = load_builtins().stage_prompts
    found = {sid for sid, text in prompts.items() if "self-review" in text.lower()}
    assert found == {"spec", "plan", "implement"}


def test_a_missing_prompt_file_is_a_loud_failure(monkeypatch):
    """A broken install saying nothing is exactly the failure the built-ins
    exist to rule out, so the loader raises rather than resolving to ""."""
    import tcw.work.resolve as resolve

    class _Missing:
        def __truediv__(self, _part):
            return self

        def read_text(self, **_kw):
            raise FileNotFoundError

    monkeypatch.setattr(resolve, "files", lambda _pkg: _Missing())
    resolve.load_builtins.cache_clear()
    try:
        with pytest.raises(resolve.ResolveError) as e:
            resolve.load_builtins()
    finally:
        resolve.load_builtins.cache_clear()
    # `implement` is first in sorted order, so it is the stage that reports.
    assert "implement" in str(e.value) and "tcw/work/prompts" in str(e.value)


def test_the_prompts_are_in_the_built_wheel(tmp_path):
    """Package data, not source-tree files. Reading the zip rather than
    installing it is also what proves the content survives a zipimport-style
    install, where no path composed from `__file__` would resolve."""
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps",
         "--no-build-isolation", "-w", str(tmp_path), str(REPO)],
        check=True, capture_output=True)
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1, wheels
    with zipfile.ZipFile(wheels[0]) as z:
        members = {n for n in z.namelist()
                   if n.startswith("tcw/work/prompts/") and n.endswith(".md")}
        assert {Path(n).stem for n in members} == SHIPPED
        for name in members:
            assert z.read(name).decode("utf-8").strip()
