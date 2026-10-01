"""A blocker edit whose cycle check cannot see through an item — a damaged
`state.yaml`, or a slug two folders hold — is refused, naming the item, unless
a cycle is found anyway (spec:
2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read)."""

import shutil
from datetime import date

import pytest
import yaml

from test_cross_node_blocker_cycles import (CYCLE, folder, graph, new,  # noqa: F401
                                            state_bytes, store, tcw)

UNREADABLE = "cannot be read"



def damage(st, slug) -> None:
    (folder(st, slug) / "state.yaml").write_text("key: [unclosed\n")


def chain(graph):
    """In `pa`: `x` blocked by `y`, `y` blocked by `z`."""
    a = store(graph, "pa")
    x, y, z = new(a, "X"), new(a, "Y"), new(a, "Z")
    a.add_blocker(x, y)
    a.add_blocker(y, z)
    return a, x, y, z


# ── 1: a damaged item on the path ────────────────────────────────────────────


def test_a_damaged_item_on_the_path_refuses_the_edit(graph):
    a, x, y, z = chain(graph)
    damage(a, y)
    before = state_bytes(a, z)
    out = tcw(graph / "pa", "edit", z, "--blocked-by", x)
    assert out.returncode != 0, out.stdout
    assert y in out.stderr and UNREADABLE in out.stderr and "unknown" in out.stderr, out.stderr
    assert state_bytes(a, z) == before


# ── 2: in another project, named with its project id ────────────────────────


def test_a_damaged_item_in_another_project_is_named_with_its_project(graph):
    a, b = store(graph, "pa"), store(graph, "pb")
    x, z, y = new(a, "X"), new(a, "Z"), new(b, "Y")
    a.add_blocker(x, f"pb/{y}")
    damage(b, y)
    out = tcw(graph / "pa", "edit", z, "--blocked-by", x)
    assert out.returncode != 0 and UNREADABLE in out.stderr, out.stderr
    assert f"pb/{y}" in out.stderr, out.stderr


# ── 3, 4: a cycle found anyway is refused as a cycle ─────────────────────────

def test_a_cycle_through_readable_items_wins(graph):
    a, x, y, z = chain(graph)
    w = new(a, "W")
    a.add_blocker(x, w)
    a.add_blocker(w, z)
    damage(a, y)
    out = tcw(graph / "pa", "edit", z, "--blocked-by", x)
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr
    assert UNREADABLE not in out.stderr, out.stderr


def test_blocks_refuses_a_cycle_behind_a_damaged_path(graph):
    """`s`'s first blocker leads through a damaged item, its second closes a
    real cycle: the walks are decided together, so the first cannot hide it."""
    a = store(graph, "pa")
    s, t, p, q, y = (new(a, n) for n in ("S", "T", "P", "Q", "Y"))
    a.add_blocker(p, y)
    a.add_blocker(q, t)
    a.add_blocker(s, p)
    a.add_blocker(s, q)
    damage(a, y)
    out = tcw(graph / "pa", "edit", s, "--blocks", t)
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr


# ── 5: update_work and create_work ───────────────────────────────────────────


def test_update_work_refuses(graph):
    a, x, y, z = chain(graph)
    damage(a, y)
    with pytest.raises(ValueError, match=UNREADABLE):
        a.update_work(z, blockers=[x])



def test_creating_an_item_refuses(graph):
    a, x, y, z = chain(graph)
    damage(a, y)
    out = tcw(graph / "pa", "new", "The new one", "--blocked-by", x)
    assert out.returncode != 0 and UNREADABLE in out.stderr, out.stderr
    assert a.get(f"{date.today().isoformat()}-the-new-one") is None


# ── 6: a slug two folders hold ───────────────────────────────────────────────


def test_an_ambiguous_slug_on_the_path_refuses_the_edit(graph):
    a, x, y, z = chain(graph)
    here = folder(a, y)
    shutil.copytree(here, here.parent.parent / "active" / y)
    out = tcw(graph / "pa", "edit", z, "--blocked-by", x)
    assert out.returncode != 0, out.stdout
    assert y in out.stderr and "more than one folder" in out.stderr, out.stderr
    assert "merge any files it lacks" in out.stderr.lower(), out.stderr
    assert "state.yaml" not in out.stderr, out.stderr       # nothing to fix there


# ── 2 (goal), 4: decided once across every blocker of one call ───────────────

def test_a_cycle_through_a_second_added_blocker_wins(graph):
    a, x, y, z = chain(graph)
    w = new(a, "W")
    a.add_blocker(w, z)
    damage(a, y)
    out = tcw(graph / "pa", "edit", z, "--blocked-by", x, "--blocked-by", w)
    assert out.returncode != 0 and CYCLE in out.stderr, out.stderr


def test_blocks_refuses_a_damaged_path_alone(graph):
    """The `--blocks` half on its own: no cycle, one proposed blocker leading
    through a damaged item."""
    a = store(graph, "pa")
    s, t, p, y = (new(a, n) for n in ("S", "T", "P", "Y"))
    a.add_blocker(p, y)
    a.add_blocker(s, p)
    damage(a, y)
    before = (state_bytes(a, s), state_bytes(a, t))
    # With another change in the same edit: a refusal only when the reverse
    # link is written would leave the new title behind.
    out = tcw(graph / "pa", "edit", s, "--blocks", t, "--title", "Renamed")
    assert out.returncode != 0 and UNREADABLE in out.stderr and y in out.stderr, out.stderr
    assert (state_bytes(a, s), state_bytes(a, t)) == before


# ── 7: what is not refused ───────────────────────────────────────────────────

def _off_the_path(graph):
    a = store(graph, "pa")
    x, z, d = new(a, "X"), new(a, "Z"), new(a, "D")
    damage(a, d)
    return tcw(graph / "pa", "edit", z, "--blocked-by", x)


def _interrupted_claim(graph):
    a, x, y, z = chain(graph)
    claiming = graph / "pa" / "docs" / "work" / ".claiming" / f"{y}-{'a' * 32}"
    claiming.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder(a, y)), str(claiming))
    return tcw(graph / "pa", "edit", z, "--blocked-by", x)


def _unreachable_project(graph):
    cfg = yaml.safe_load((graph / "tcw-config.yaml").read_text())
    cfg["connected-projects"]["children"]["gone"] = "gone"
    (graph / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    a = store(graph, "pa")
    x, z = new(a, "X"), new(a, "Z")
    a.set_field(x, "blocked_by", [{"external": "gone/some-item"}])
    return tcw(graph / "pa", "edit", z, "--blocked-by", x)


def _unblocking(graph):
    a, x, y, z = chain(graph)
    damage(a, y)
    return tcw(graph / "pa", "edit", x, "--unblocked-by", y)


@pytest.mark.parametrize("case", [_off_the_path, _interrupted_claim,
                                  _unreachable_project, _unblocking])
def test_not_refused(graph, case):
    out = case(graph)
    assert out.returncode == 0, out.stderr


def test_editing_the_damaged_item_itself_is_the_existing_refusal(graph):
    """Refused by the strict read of the item's own file, before any walk."""
    a, x, y, z = chain(graph)
    damage(a, y)
    before = state_bytes(a, y)
    out = tcw(graph / "pa", "edit", y, "--blocked-by", new(a, "Other"))
    assert out.returncode != 0, out.stdout
    assert "while parsing" in out.stderr, out.stderr
    assert "blocking cycle with this edit" not in out.stderr, out.stderr
    assert state_bytes(a, y) == before
