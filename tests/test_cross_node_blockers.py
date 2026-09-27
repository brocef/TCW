"""A blocker naming another node's item resolves against that node
(spec: 2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it;
GitHub #28)."""

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsWorkStore, init
from tcw.work.recursion import reconcile


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
    """root → pa, pb, each with a board."""
    root = node(tmp_path / "root", "root", children={"pa": "pa", "pb": "pb"})
    node(root / "pa", "pa", parent="root")
    node(root / "pb", "pb", parent="root")
    return root


def finish(st: FsWorkStore, slug: str) -> None:
    st.start(slug, force=True)
    st.complete(slug, "done", st.dod_checklist(), force=True)


def new(st: FsWorkStore, title: str, **fields) -> str:
    slug = st.create(title, created="2026-01-01").slug
    for key, value in fields.items():
        st.set_field(slug, key, value)
    return slug


def tcw(root: Path, *args: str):
    return subprocess.run(["tcw", "work", *args], cwd=str(root),
                          capture_output=True, text=True)


# ── criterion 1: start ───────────────────────────────────────────────────────

def test_start_follows_the_other_nodes_item(graph):
    a, b = FsWorkStore.open(graph / "pa"), FsWorkStore.open(graph / "pb")
    dep = new(b, "Dep")
    slug = new(a, "Needs dep")
    a.add_blocker(slug, f"pb/{dep}")
    assert a.get(slug).blocked_by == [{"external": f"pb/{dep}"}]
    with pytest.raises(ValueError, match=f"pb/{dep}"):
        a.start(slug)
    finish(b, dep)
    assert a.start(slug).status == "active"


def test_it_still_resolves_once_only_the_tombstone_is_left(graph):
    a, b = FsWorkStore.open(graph / "pa"), FsWorkStore.open(graph / "pb")
    dep = new(b, "Dep")
    slug = new(a, "Needs dep")
    a.add_blocker(slug, f"pb/{dep}")
    finish(b, dep)
    shutil.rmtree(b.path(dep))                     # what every other clone sees
    assert b.get(dep) is None and b.tombstone(dep) is not None
    assert a.unresolved_blockers(a.get(slug)) == []


# ── criterion 2: reconcile ───────────────────────────────────────────────────

def test_reconcile_names_the_item_once_its_other_node_blocker_resolves(graph):
    root = FsWorkStore.open(graph)
    a, b = FsWorkStore.open(graph / "pa"), FsWorkStore.open(graph / "pb")
    epic = new(root, "Epic")
    dep = new(b, "Dep", initiative=epic)
    slug = new(a, "Needs dep", initiative=epic)
    a.add_blocker(slug, f"pb/{dep}")
    assert f"pa/{slug}" not in reconcile(graph, epic).split("**Next:**")[1]
    finish(b, dep)
    assert f"pa/{slug}" in reconcile(graph, epic).split("**Next:**")[1]


def test_reconcile_does_not_mix_up_equal_slugs_in_two_nodes(graph):
    root = FsWorkStore.open(graph)
    a, b = FsWorkStore.open(graph / "pa"), FsWorkStore.open(graph / "pb")
    epic = new(root, "Epic")
    x_a = new(a, "X", initiative=epic)
    x_b = new(b, "X", initiative=epic)
    assert x_a == x_b
    y = new(a, "Y", initiative=epic)
    a.add_blocker(y, x_a)                          # pa's own x
    finish(a, x_a)                                 # resolved; pb's x stays open
    nxt = reconcile(graph, epic).split("**Next:**")[1]
    assert f"pa/{y}" in nxt, nxt


# ── criterion 3: what still blocks ──────────────────────────────────────────

@pytest.mark.parametrize("text", ["waiting on the vendor", "pb/no-such-item",
                                  "vendor/legal review"])
def test_anything_unresolvable_keeps_blocking(graph, text):
    a = FsWorkStore.open(graph / "pa")
    slug = new(a, "Thing")
    a.add_blocker(slug, text)
    assert a.unresolved_blockers(a.get(slug)) != []


def test_a_declared_but_absent_project_blocks_and_says_why(graph):
    cfg_path = graph / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["connected-projects"]["children"]["gone"] = "gone"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    a = FsWorkStore.open(graph / "pa")
    slug = new(a, "Thing")
    a.add_blocker(slug, "gone/some-item")
    [label] = a.unresolved_blockers(a.get(slug))
    assert "gone/some-item" in label and "gone" in label.split("gone/some-item", 1)[1]


# ── criterion 4: a tombstoned local slug ─────────────────────────────────────

def test_blocked_by_a_tombstoned_local_item_is_recorded_as_a_slug(graph):
    a = FsWorkStore.open(graph / "pa")
    dep = new(a, "Dep")
    finish(a, dep)
    shutil.rmtree(a.path(dep))
    slug = new(a, "Thing")
    a.add_blocker(slug, dep)
    assert a.get(slug).blocked_by == [{"slug": dep}]
    assert a.unresolved_blockers(a.get(slug)) == []
    a.remove_blocker(slug, dep)
    assert a.get(slug).blocked_by == []


def test_an_existing_external_entry_for_a_tombstoned_slug_no_longer_blocks(graph):
    a = FsWorkStore.open(graph / "pa")
    dep = new(a, "Dep")
    finish(a, dep)
    shutil.rmtree(a.path(dep))
    slug = new(a, "Thing")
    a.set_field(slug, "blocked_by", [{"external": dep}])
    assert a.unresolved_blockers(a.get(slug)) == []


# ── criterion 5: list agrees with start ─────────────────────────────────────

def test_list_stops_showing_a_resolved_cross_node_blocker(graph):
    a, b = FsWorkStore.open(graph / "pa"), FsWorkStore.open(graph / "pb")
    dep = new(b, "Dep")
    slug = new(a, "Needs dep")
    a.add_blocker(slug, f"pb/{dep}")
    assert "blocked-by" in tcw(graph / "pa", "list").stdout
    finish(b, dep)
    out = tcw(graph / "pa", "list")
    assert "blocked-by" not in out.stdout, out.stdout


# ── review findings ─────────────────────────────────────────────────────────

def test_an_old_external_entry_resolves_where_the_folder_is_still_present(graph):
    """The machine that completed the item still has its folder; it must read
    the entry the way every other clone does."""
    a = FsWorkStore.open(graph / "pa")
    dep = new(a, "Dep")
    finish(a, dep)
    assert a.get(dep) is not None
    slug = new(a, "Thing")
    a.set_field(slug, "blocked_by", [{"external": dep}])
    assert a.unresolved_blockers(a.get(slug)) == []


@pytest.mark.parametrize("text", ["vendor/legal review",
                                  "https://github.com/x/y/issues/1",
                                  "vendor/legal/review", "pb/foo/"])
def test_prose_with_a_slash_is_labelled_as_written(graph, text):
    a = FsWorkStore.open(graph / "pa")
    slug = new(a, "Thing")
    a.add_blocker(slug, text)
    assert a.unresolved_blockers(a.get(slug)) == [f"external: {text}"]


def test_a_label_copied_from_list_removes_the_blocker(graph):
    cfg_path = graph / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["connected-projects"]["children"]["gone"] = "gone"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    a = FsWorkStore.open(graph / "pa")
    slug = new(a, "Thing")
    a.add_blocker(slug, "gone/some-item")
    [label] = a.unresolved_blockers(a.get(slug))
    assert label != "external: gone/some-item"     # it carries a reason
    a.remove_blocker(slug, label)
    assert a.get(slug).blocked_by == []
