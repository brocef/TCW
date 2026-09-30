"""A blocker cycle that runs through items in other connected projects is refused
like one within a project (spec: 2026-09-29-detect-a-blocker-cycle-that-runs-across-nodes)."""

import os
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsWorkStore, init


def node(path: Path, pid: str, *, parent: str | None = None,
         children: dict | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if parent is None:
        for cmd in (["init", "-q"], ["config", "user.email", "t@t"],
                    ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(path), *cmd], check=True)
    init(["work"], path, pid)
    cfg = yaml.safe_load((path / "tcw-config.yaml").read_text()) or {}
    links = {}
    if parent:
        links["parent"] = {parent: ".."}
    if children:
        links["children"] = children
    if links:
        cfg["connected-projects"] = links
    (path / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return path


@pytest.fixture
def graph(tmp_path) -> Path:
    """r → pa, pb, pc, each with a board."""
    root = node(tmp_path / "r", "r", children={"pa": "pa", "pb": "pb", "pc": "pc"})
    for pid in ("pa", "pb", "pc"):
        node(root / pid, pid, parent="r")
    return root


def store(graph: Path, pid: str) -> FsWorkStore:
    return FsWorkStore.open(graph / pid)


def new(st: FsWorkStore, title: str) -> str:
    return st.create(title, created="2026-01-01").slug


def tcw(cwd: Path, *args: str):
    return subprocess.run(["tcw", "work", *args], cwd=str(cwd),
                          capture_output=True, text=True)


def folder(st: FsWorkStore, slug: str) -> Path:
    return st.node_root / st.locate(slug)


def state_bytes(st: FsWorkStore, slug: str) -> bytes:
    return (folder(st, slug) / "state.yaml").read_bytes()


CYCLE = "would create a blocking cycle"


@pytest.fixture
def pair(graph):
    """`x` in pa, blocked by `pb/y`."""
    a, b = store(graph, "pa"), store(graph, "pb")
    x, y = new(a, "X"), new(b, "Y")
    a.add_blocker(x, f"pb/{y}")
    return a, b, x, y


# ── 1, 2, 3: the edit that closes the cycle is refused ───────────────────────


def test_a_two_node_cycle_is_refused(graph, pair):
    a, b, x, y = pair
    before = state_bytes(b, y)
    out = tcw(graph / "pb", "edit", y, "--blocked-by", f"pa/{x}")
    assert out.returncode != 0, out.stdout
    assert CYCLE in out.stderr, out.stderr
    assert state_bytes(b, y) == before


def test_a_three_node_cycle_is_refused(graph):
    a, b, c = store(graph, "pa"), store(graph, "pb"), store(graph, "pc")
    x, y, z = new(a, "X"), new(b, "Y"), new(c, "Z")
    a.add_blocker(x, f"pb/{y}")
    b.add_blocker(y, f"pc/{z}")
    out = tcw(graph / "pc", "edit", z, "--blocked-by", f"pa/{x}")
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr


def test_the_cycle_is_refused_when_edited_from_another_node(graph, pair):
    a, b, x, y = pair
    before = state_bytes(b, y)
    out = tcw(graph / "pa", "edit", f"pb/{y}", "--blocked-by", f"pa/{x}")
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr
    assert state_bytes(b, y) == before


# ── 4: --blocks ──────────────────────────────────────────────────────────────


def test_blocks_closing_a_cross_node_cycle_is_refused(graph):
    a, b = store(graph, "pa"), store(graph, "pb")
    x, x2, y = new(a, "X"), new(a, "X two"), new(b, "Y")
    a.add_blocker(x2, f"pb/{y}")
    b.add_blocker(y, f"pa/{x}")
    before = (state_bytes(a, x), state_bytes(a, x2))
    # With another change in the same edit: a refusal that comes only after
    # the fields were written would leave the new title behind.
    out = tcw(graph / "pa", "edit", x2, "--blocks", x, "--title", "Renamed")
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr
    assert (state_bytes(a, x), state_bytes(a, x2)) == before


# ── 5: update_work, which the web app's PATCH calls ──────────────────────────


def test_update_work_refuses_the_cycle(pair):
    a, b, x, y = pair
    with pytest.raises(ValueError, match=CYCLE):
        b.update_work(y, blockers=[f"pa/{x}"])


# ── 6: create_work, through a blocker naming a slug that does not exist yet ─


def test_creating_an_item_that_closes_a_cycle_is_refused(graph):
    a, b = store(graph, "pa"), store(graph, "pb")
    y = new(b, "Y")
    future = f"{date.today().isoformat()}-the-new-one"
    b.add_blocker(y, f"pa/{future}")
    out = tcw(graph / "pa", "new", "The new one", "--blocked-by", f"pb/{y}")
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr
    assert a.get(future) is None


def test_creating_an_item_that_closes_a_local_cycle_is_refused(graph):
    a = store(graph, "pa")
    y = new(a, "Y")
    future = f"{date.today().isoformat()}-the-new-one"
    a.set_field(y, "blocked_by", [{"external": future}])
    out = tcw(graph / "pa", "new", "The new one", "--blocked-by", y)
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr
    assert a.get(future) is None


# ── 7: no false refusals ─────────────────────────────────────────────────────

@pytest.mark.parametrize("ref", ["pb/{y}", "zz/x", "pb/nosuch", "vendor/legal review"])
def test_blockers_without_a_cycle_are_accepted(graph, pair, ref):
    a, b, x, y = pair
    z = new(a, "Z")
    out = tcw(graph / "pa", "edit", z, "--blocked-by", ref.replace("{y}", y))
    assert out.returncode == 0, out.stderr


# ── 8: a stored cycle does not trap edits ────────────────────────────────────

def test_a_stored_cycle_leaves_other_edits_and_the_fix_possible(graph, pair):
    a, b, x, y = pair
    b.set_field(y, "blocked_by", [{"external": f"pa/{x}"}])      # stored, unchecked
    other = new(b, "Other")
    out = tcw(graph / "pb", "edit", y, "--blocked-by", other)
    assert out.returncode == 0, out.stderr
    out = tcw(graph / "pb", "edit", y, "--unblocked-by", f"pa/{x}")
    assert out.returncode == 0, out.stderr
    assert {"external": f"pa/{x}"} not in b.get(y).blocked_by


# ── 9: one store reached by two spellings ────────────────────────────────────

def _case_insensitive(path: Path) -> bool:
    return Path(str(path).swapcase()).exists()


def test_one_store_by_two_spellings_is_one_store(graph):
    if not _case_insensitive(graph):
        pytest.skip("the disk is case-sensitive")
    a, b = store(graph, "pa"), store(graph, "pb")
    x, y = new(a, "X"), new(b, "Y")
    a.add_blocker(x, f"pb/{y}")
    # `pa` now reaches pb's board through a spelling differing only in case.
    cfg = yaml.safe_load((graph / "tcw-config.yaml").read_text())
    cfg["connected-projects"]["children"]["pb"] = "PB"
    (graph / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    with pytest.raises(ValueError, match=CYCLE):
        FsWorkStore.open(graph / "pb").add_blocker(y, f"pa/{x}")


# ── 10: another node's broken state does not fail an edit here ───────────────

def test_an_interrupted_claim_elsewhere_does_not_fail_the_edit(graph):
    a, b = store(graph, "pa"), store(graph, "pb")
    x, y = new(a, "X"), new(b, "Y")
    b.add_blocker(y, f"pa/{new(a, 'Unrelated')}")
    claiming = graph / "pb" / "docs" / "work" / ".claiming" / f"{y}-{'a' * 32}"
    claiming.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder(b, y)), str(claiming))
    out = tcw(graph / "pa", "edit", x, "--blocked-by", f"pb/{y}")
    assert out.returncode == 0, out.stderr


def test_a_walk_through_an_interrupted_claim_elsewhere_does_not_fail(graph):
    """The walk itself crosses into the other store and meets the claim."""
    a, b = store(graph, "pa"), store(graph, "pb")
    x, z, y = new(a, "X"), new(a, "Z"), new(b, "Y")
    a.add_blocker(x, f"pb/{y}")
    claiming = graph / "pb" / "docs" / "work" / ".claiming" / f"{y}-{'a' * 32}"
    claiming.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder(b, y)), str(claiming))
    out = tcw(graph / "pa", "edit", z, "--blocked-by", x)
    assert out.returncode == 0, out.stderr


def test_an_interrupted_claim_here_does_not_fail_creating_an_item(graph):
    a = store(graph, "pa")
    p, q = new(a, "P"), new(a, "Q")
    a.add_blocker(p, q)
    claiming = graph / "pa" / "docs" / "work" / ".claiming" / f"{q}-{'a' * 32}"
    claiming.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder(a, q)), str(claiming))
    out = tcw(graph / "pa", "new", "New thing", "--blocked-by", p)
    assert out.returncode == 0, out.stderr


def test_a_plain_string_blocker_does_not_crash_blocks(graph):
    a = store(graph, "pa")
    x, z = new(a, "X"), new(a, "Z")
    a.set_field(x, "blocked_by", ["some-text"])               # hand-edited
    out = tcw(graph / "pa", "edit", x, "--blocks", z)
    assert "Traceback" not in out.stderr, out.stderr
