"""`delegate` and `reconcile` pass through a node that keeps no board
(spec: 2026-09-09-descend-through-a-storeless-routing-node-in-delegate-and-reconcile;
GitHub #30)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import init


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


# ── criterion 2: a node with a board is the target; reconcile looks below it ─

@pytest.fixture
def stacked(tmp_path) -> Path:
    root = node(tmp_path / "root", "root", board=True, children={"x": "x"})
    node(root / "x", "x", board=True, parent="root", children={"y": "y"})
    node(root / "x" / "y", "y", board=True, parent="x")
    return root


# ── criterion 3: declared behind a routing node, absent here ────────────────


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


