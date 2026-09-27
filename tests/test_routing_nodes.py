"""`delegate` and `reconcile` pass through a node that keeps no board
(spec: 2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile;
GitHub #30)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init
from tcw.work.recursion import delegate, reconcile


def node(path: Path, pid: str, *, board: bool, parent: str | None = None,
         children: dict | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists() and parent is None:
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    if board:
        init(["work"], path, pid)
    else:
        (path / "tcw-config.yaml").write_text(f"id: {pid}\n")
    import yaml
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


def slice_of(root: Path, epic: str, title: str = "Slice") -> str:
    st = FsWorkStore.open(root)
    slug = st.create(title, created="2026-01-01").slug
    st.set_field(slug, "initiative", epic)
    return slug


@pytest.fixture
def routed(tmp_path) -> Path:
    """root (board) → mid (no board) → pa, pb, pc (boards) — the issue's graph."""
    root = node(tmp_path / "root", "root", board=True, children={"mid": "mid"})
    node(root / "mid", "mid", board=False, parent="root",
         children={"pa": "pa", "pb": "pb", "pc": "pc"})
    for name in ("pa", "pb", "pc"):
        node(root / "mid" / name, name, board=True, parent="mid")
    return root


# ── criterion 1 ──────────────────────────────────────────────────────────────

def test_delegate_reaches_a_board_behind_a_routing_node(routed):
    doc = delegate(routed, "pa", "A slice")
    assert doc.resolve().is_relative_to((routed / "mid" / "pa").resolve())


def test_reconcile_lists_slices_behind_a_routing_node(routed):
    epic = FsWorkStore.open(routed).create("Epic", created="2026-01-01").slug
    for name in ("pa", "pb", "pc"):
        slice_of(routed / "mid" / name, epic)
    block = reconcile(routed, epic)
    for name in ("pa", "pb", "pc"):
        assert f"| {name} | 2026-01-01-slice |" in block, block


# ── criterion 2: a node with a board is the target; reconcile looks below it ─

@pytest.fixture
def stacked(tmp_path) -> Path:
    root = node(tmp_path / "root", "root", board=True, children={"x": "x"})
    node(root / "x", "x", board=True, parent="root", children={"y": "y"})
    node(root / "x" / "y", "y", board=True, parent="x")
    return root


def test_reconcile_looks_below_a_child_with_a_board(stacked):
    epic = FsWorkStore.open(stacked).create("Epic", created="2026-01-01").slug
    slice_of(stacked / "x" / "y", epic)
    assert "| y | 2026-01-01-slice |" in reconcile(stacked, epic)


def test_delegate_stops_at_the_nearest_board(stacked):
    with pytest.raises(ValueError) as refused:
        delegate(stacked, "y", "Too deep")
    assert "no child node 'y'" in str(refused.value)
    assert "children: x" in str(refused.value)


# ── criterion 3: declared behind a routing node, absent here ────────────────

def test_a_declared_target_behind_a_routing_node_that_is_absent(tmp_path):
    root = node(tmp_path / "root", "root", board=True, children={"mid": "mid"})
    node(root / "mid", "mid", board=False, parent="root", children={"gone": "gone"})
    with pytest.raises(ValueError, match="declared in .* but is not reachable"):
        delegate(root, "gone", "Nowhere")


# ── criterion 4: the topology view is unchanged ─────────────────────────────

def test_nodes_still_prints_the_direct_topology(routed, monkeypatch, capsys):
    monkeypatch.chdir(routed)
    assert main(["work", "nodes"]) == 0
    out = capsys.readouterr().out
    assert [ln.split()[0] for ln in out.split("children:", 1)[1].splitlines() if ln.strip()] \
        == ["mid"], out                    # the direct topology, as before


# ── review finding: one registry, opened at the root ───────────────────────

def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def test_a_routing_node_outside_a_worktree_does_not_break_delegate(tmp_path):
    """From a linked worktree of the root, a routing node in another repository
    opens a registry that sees the *primary* checkout's root, which does not
    declare it. Walking that registry made `delegate` refuse even a direct
    child; the walk now uses the root's own registry throughout."""
    import yaml
    main_root = node(tmp_path / "R", "root", board=True, children={"x": "x"})
    node(main_root / "x", "x", board=True, parent="root")
    _git(main_root, "add", "-A")
    _git(main_root, "commit", "-qm", "base")
    mid = node(tmp_path / "mid", "mid", board=False, children={"pa": "pa"})
    cfg = yaml.safe_load((mid / "tcw-config.yaml").read_text())
    cfg["connected-projects"]["parent"] = {"root": "../R"}
    (mid / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    node(mid / "pa", "pa", board=True, parent="mid")
    _git(mid, "add", "-A")
    _git(mid, "commit", "-qm", "m")
    wt = tmp_path / "W"
    _git(main_root, "worktree", "add", "-q", str(wt), "-b", "feat")
    cfg = yaml.safe_load((wt / "tcw-config.yaml").read_text())
    cfg["connected-projects"]["children"] = {"x": "x", "mid": "../mid"}
    (wt / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))

    assert delegate(wt, "x", "Direct").resolve().is_relative_to((wt / "x").resolve())
    assert delegate(wt, "pa", "Routed").resolve().is_relative_to((mid / "pa").resolve())
