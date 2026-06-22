import subprocess
from pathlib import Path

import pytest

from tcw.store.base import IllegalTransition, MultipleMatch, topo_order
from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


# ── init / slug ──────────────────────────────────────────────────────────────

def test_init_gitkeep_persistence(tmp_path):
    root = node(tmp_path)
    for s in ("inbox", "backlog", "active", "completed"):
        assert (root / "docs" / "work" / s / ".gitkeep").is_file()
    assert not (root / "docs" / "work" / "blocked").exists()


def test_slug_generation_collision_and_immutability(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("Fix the bug", created="2026-01-01")
    assert a.slug == "2026-01-01-fix-the-bug"
    b = st.create("Fix the bug", created="2026-01-01")
    assert b.slug == "2026-01-01-fix-the-bug-2"        # collision suffix
    st.set_field(a.slug, "title", "Renamed")           # title drifts...
    assert st.get(a.slug).title == "Renamed"
    assert st.get(a.slug).slug == a.slug               # ...slug is frozen


def test_body_path_points_at_content_md(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    body = st.body_path(item.slug)
    assert body == st.path(item.slug) / "content.md"
    assert body.exists()
    assert st.body_path("no-such-slug") is None


def test_multiple_match_resolution_error(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    for s in ("active", "backlog"):
        d = root / "docs/work" / s / "dup"
        d.mkdir()
        (d / "state.yaml").write_text("slug: dup\n")     # state.yaml is the item marker
    with pytest.raises(MultipleMatch):
        st.get("dup")


# ── transitions ──────────────────────────────────────────────────────────────

def test_legal_transition_lifecycle(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.get(item.slug).status == "backlog"
    assert st.start(item.slug).status == "active"
    assert st.complete(item.slug, "done", ["acked"]).status == "completed"
    assert st.get(item.slug).resolution == "done"


def test_completed_is_a_sink(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    with pytest.raises(IllegalTransition):
        st.start(item.slug)               # completed → active refused


def test_illegal_transitions_refused(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    with pytest.raises(IllegalTransition):
        st.complete(item.slug, "done", [])    # backlog → completed (only from active)
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    with pytest.raises(IllegalTransition):
        st.start(item.slug)                   # completed → active (sink)


def test_drop_only_from_inbox_or_backlog(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    st.start(item.slug)
    with pytest.raises(IllegalTransition):
        st.drop(item.slug)                    # active can't be dropped


def test_blocked_by_read_from_state_yaml(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    assert st.get(item.slug).blocked_by == []          # absent key → empty
    st.set_field(item.slug, "blocked_by", [{"external": "vendor"}])
    assert st.get(item.slug).blocked_by == [{"external": "vendor"}]


# ── query / resolution after move / boundedness ──────────────────────────────

def test_list_status_filter(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    st.start(b.slug)
    assert {i.slug for i in st.query(status="backlog")} == {"2026-01-01-a"}
    assert {i.slug for i in st.query(status="active")} == {"2026-01-02-b"}


def test_resolution_after_move_and_node_bounded(tmp_path):
    parent = node(tmp_path, "parent")
    pst = FsWorkStore.open(parent)
    item = pst.create("Task", created="2026-01-01")
    pst.start(item.slug)                       # folder moved backlog → active
    assert pst.get(item.slug).status == "active"   # resolves after the move
    # a child node's item is invisible to the parent store (bounded — A.5)
    child = node(parent, "child")
    cst = FsWorkStore.open(child)
    citem = cst.create("Child task", created="2026-01-01")
    assert pst.get(citem.slug) is None


def test_malformed_state_yaml_degrades(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    (root / "docs/work/backlog" / item.slug / "state.yaml").write_text("{not: valid: yaml:")
    got = st.get(item.slug)                    # no crash
    assert got is not None and got.status == "backlog"


# ── blocked-by relation ──────────────────────────────────────────────────────

def test_add_and_remove_blocker_roundtrip(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    st.add_blocker(a.slug, b.slug)
    assert st.get(a.slug).blocked_by == [{"slug": b.slug}]
    st.add_blocker(a.slug, b.slug)                      # idempotent
    assert st.get(a.slug).blocked_by == [{"slug": b.slug}]
    st.remove_blocker(a.slug, b.slug)
    assert st.get(a.slug).blocked_by == []
    st.remove_blocker(a.slug, b.slug)                   # absent → no-op


def test_external_blocker_stored(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    st.add_blocker(a.slug, "waiting on vendor")         # unresolvable → external
    assert st.get(a.slug).blocked_by == [{"external": "waiting on vendor"}]
    st.remove_blocker(a.slug, "waiting on vendor")
    assert st.get(a.slug).blocked_by == []


def test_self_block_refused(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    with pytest.raises(ValueError):
        st.add_blocker(a.slug, a.slug)


def test_cycle_refused_direct_and_transitive(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    c = st.create("C", created="2026-01-03")
    st.add_blocker(a.slug, b.slug)                      # A blocked by B
    with pytest.raises(ValueError):
        st.add_blocker(b.slug, a.slug)                  # B blocked by A → direct cycle
    st.add_blocker(b.slug, c.slug)                      # B blocked by C
    with pytest.raises(ValueError):
        st.add_blocker(c.slug, a.slug)                  # C blocked by A → A→B→C→A cycle


# ── gating: unresolved blockers ─────────────────────────────────────────────

def test_start_gated_on_unresolved_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    with pytest.raises(ValueError):
        st.start(target.slug)                          # blocker not completed
    assert st.start(target.slug, force=True).status == "active"


def test_start_ungated_when_blocker_completed_or_dropped(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(blocker.slug)
    st.complete(blocker.slug, "done", [])
    assert st.start(target.slug).status == "active"    # completed blocker → resolved


def test_start_passes_on_dropped_blocker_silently(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.drop(blocker.slug)                              # vanished → resolved, no warning
    assert st.start(target.slug).status == "active"


def test_complete_gated_on_unresolved_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)
    with pytest.raises(ValueError):
        st.complete(target.slug, "done", [])           # still blocked
    assert st.complete(target.slug, "done", [], force=True).status == "completed"


# ── CLI: DoD gate ────────────────────────────────────────────────────────────

def test_cli_complete_requires_confirm(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    main(["work", "start", slug])
    assert main(["work", "complete", slug, "--resolution", "done"]) == 1   # no --confirm
    assert FsWorkStore.open(root).get(slug).status == "active"
    assert "Definition of Done" in capsys.readouterr().out
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"


# ── topo_order / board ───────────────────────────────────────────────────────

def test_topo_order_blocker_before_blocked(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")           # will be blocked by B
    b = st.create("B", created="2026-01-02")
    st.add_blocker(a.slug, b.slug)
    ordered = [i.slug for i in st.board()]
    assert ordered.index(b.slug) < ordered.index(a.slug)


def test_topo_order_stable_on_ties(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    c = st.create("C", created="2026-01-03")           # no edges → input order kept
    st.add_blocker(b.slug, "external wait")            # external is not a graph node
    ordered = [i.slug for i in st.board()]
    assert ordered == [a.slug, b.slug, c.slug]         # external doesn't reorder


def test_topo_order_ignores_blocker_outside_set(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    backlog_blocker = st.create("Blocker", created="2026-01-01")
    x = st.create("X", created="2026-01-02")
    y = st.create("Y", created="2026-01-03")
    st.add_blocker(x.slug, backlog_blocker.slug)        # blocker stays in backlog
    st.start(x.slug, force=True)
    st.start(y.slug)
    ordered = [i.slug for i in st.board(status="active")]
    assert ordered == [x.slug, y.slug]                  # blocker not in set → no reorder


# ── CLI: edit / new --blocked-by / --force / ordered list ───────────────────

def test_cli_edit_blocked_by_and_blocks(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    assert main(["work", "edit", a.slug, "--blocked-by", b.slug]) == 0
    assert FsWorkStore.open(root).get(a.slug).blocked_by == [{"slug": b.slug}]
    # reverse direction: a now blocks b's sibling c
    c = st.create("C", created="2026-01-03")
    assert main(["work", "edit", a.slug, "--blocks", c.slug]) == 0
    assert FsWorkStore.open(root).get(c.slug).blocked_by == [{"slug": a.slug}]
    assert main(["work", "edit", a.slug, "--unblocked-by", b.slug]) == 0
    assert FsWorkStore.open(root).get(a.slug).blocked_by == []


def test_cli_edit_blocks_nonexistent_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    a = FsWorkStore.open(root).create("A", created="2026-01-01")
    assert main(["work", "edit", a.slug, "--blocks", "nope"]) == 1


def test_cli_new_blocked_by(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    b = FsWorkStore.open(root).create("B", created="2026-01-01")
    assert main(["work", "new", "A", "--blocked-by", f"{b.slug}, , extra"]) == 0
    items = FsWorkStore.open(root).query(status="backlog")
    a = next(i for i in items if i.title == "A")
    assert a.blocked_by == [{"slug": b.slug}, {"external": "extra"}]


def test_cli_new_blocked_by_attach_failure_returns_nonzero(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    for s in ("active", "backlog"):
        d = root / "docs/work" / s / "dup"
        d.mkdir()
        (d / "state.yaml").write_text("slug: dup\n")        # two real items named "dup"
    rc = main(["work", "new", "A", "--blocked-by", "dup"])   # ambiguous ref → attach fails
    out = capsys.readouterr().out.strip()
    assert rc == 1                                           # non-zero on attach failure
    assert (root / "docs/work/backlog" / out).is_dir()      # item still created + slug printed


def test_cli_new_and_start_emit_next_step_hints(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "new", "A"]) == 0
    new_out = capsys.readouterr()
    slug = new_out.out.strip()
    assert "\n" not in slug                                  # stdout is just the slug…
    assert "tcw work start" in new_out.err and slug in new_out.err   # …hint is on stderr

    assert main(["work", "start", slug]) == 0
    start_out = capsys.readouterr()
    assert start_out.out.strip() == f"started {slug}"        # stdout unchanged
    assert "tcw work complete" in start_out.err and slug in start_out.err


def test_cli_new_epic_omits_start_hint(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "E", "--epic"]) == 0         # epic's next step is delegate
    assert "tcw work start" not in capsys.readouterr().err


def test_cli_edit_ambiguous_slug_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    (root / "docs/work/active/dup").mkdir()
    (root / "docs/work/backlog/dup").mkdir()
    assert main(["work", "edit", "dup", "--blocked-by", "x"]) == 1


def test_cli_complete_blocker_gate_before_dod(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    blocker = st.create("Blocker", created="2026-01-01")
    target = st.create("Target", created="2026-01-02")
    st.add_blocker(target.slug, blocker.slug)
    st.start(target.slug, force=True)
    rc = main(["work", "complete", target.slug, "--resolution", "done", "--confirm"])
    assert rc == 1
    out = capsys.readouterr()
    assert "blocked by" in out.err and "Definition of Done" not in out.out  # fail-fast
    assert main(["work", "complete", target.slug, "--resolution", "done",
                 "--confirm", "--force"]) == 0


def test_malformed_blocked_by_entry_degrades(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "blocked_by", [{"note": "garbage"}])
    assert st.unresolved_blockers(st.get(item.slug)) == []   # skipped, no KeyError
    monkeypatch.chdir(root)
    assert main(["work", "show", item.slug]) == 0            # show doesn't crash
    assert main(["work", "list"]) == 0                       # list doesn't crash


# ── priority ─────────────────────────────────────────────────────────────────

def test_priority_order_specified_above_unspecified_desc(tmp_path):
    from tcw.store.base import priority_order
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")               # no priority
    b = st.create("B", created="2026-01-02", priority=1)
    c = st.create("C", created="2026-01-03")               # no priority
    d = st.create("D", created="2026-01-04", priority=5)
    ordered = [i.slug for i in priority_order(st.query(status="backlog"))]
    # specified desc (D=5, B=1) first; unspecified keep creation order (A, C)
    assert ordered == [d.slug, b.slug, a.slug, c.slug]


def test_priority_default_unspecified_keeps_creation_order(tmp_path):
    from tcw.store.base import priority_order
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("A", created="2026-01-01")
    b = st.create("B", created="2026-01-02")
    assert a.priority is None
    assert [i.slug for i in priority_order([a, b])] == [a.slug, b.slug]


def test_board_priority_cannot_jump_a_blocker(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    blocker = st.create("Blocker", created="2026-01-01")   # low/no priority
    blocked = st.create("Blocked", created="2026-01-02", priority=9)
    st.add_blocker(blocked.slug, blocker.slug)
    ordered = [i.slug for i in st.board(status="backlog")]
    # priority wants Blocked first, but its blocker is a hard constraint
    assert ordered.index(blocker.slug) < ordered.index(blocked.slug)


def test_priority_persists_create_and_set_field(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01", priority=3)
    assert FsWorkStore.open(root).get(a.slug).priority == 3
    st.set_field(a.slug, "priority", 7)
    assert FsWorkStore.open(root).get(a.slug).priority == 7


def test_cli_new_and_edit_priority_reorders_list(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    assert main(["work", "new", "B", "--priority", "5"]) == 0
    b = next(i for i in FsWorkStore.open(root).query(status="backlog") if i.title == "B")
    assert FsWorkStore.open(root).get(b.slug).priority == 5
    # B (priority 5) sorts above A (unspecified)
    assert [i.slug for i in FsWorkStore.open(root).board(status="backlog")][0] == b.slug
    # raise A above B via edit
    assert main(["work", "edit", a.slug, "--priority", "9"]) == 0
    assert FsWorkStore.open(root).get(a.slug).priority == 9
    assert [i.slug for i in FsWorkStore.open(root).board(status="backlog")][0] == a.slug


# ── list: completed hidden by default ────────────────────────────────────────

def _make_completed(st):
    item = st.create("Done thing", created="2026-01-01")
    st.start(item.slug)
    st.complete(item.slug, "done", [])
    return item


def test_cli_list_hides_completed_by_default(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    live = st.create("Live one", created="2026-01-02")
    done = _make_completed(st)
    assert main(["work", "list"]) == 0
    out = capsys.readouterr().out
    assert live.slug in out
    assert done.slug not in out                 # completed hidden by default


def test_cli_list_status_completed_still_shows(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    done = _make_completed(st)
    assert main(["work", "list", "--status", "completed"]) == 0
    assert done.slug in capsys.readouterr().out  # explicit filter honored


def test_cli_list_all_includes_completed(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    live = st.create("Live one", created="2026-01-02")
    done = _make_completed(st)
    assert main(["work", "list", "--all"]) == 0
    out = capsys.readouterr().out
    assert live.slug in out and done.slug in out  # --all = full board


# ── list: priority column ────────────────────────────────────────────────────

def test_cli_list_shows_priority_column(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    hot = st.create("Hot", created="2026-01-01", priority=7)
    cold = st.create("Cold", created="2026-01-02")        # unspecified
    assert main(["work", "list"]) == 0
    rows = {ln.split(" | ")[0]: ln.split(" | ")
            for ln in capsys.readouterr().out.splitlines()}
    # row: slug | status | phase | priority | title
    assert rows[hot.slug][3] == "7"
    assert rows[cold.slug][3] == "-"
    assert rows[hot.slug][4] == "Hot"                     # title still follows


def test_cli_work_init_mirrors_top_level(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = tmp_path / "fresh"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.chdir(root)
    assert main(["work", "init"]) == 0
    comp_out = capsys.readouterr().out
    for s in ("inbox", "backlog", "active", "completed"):
        assert (root / "docs" / "work" / s / ".gitkeep").is_file()
    assert main(["init", "work"]) == 0
    assert comp_out == capsys.readouterr().out


# ── nested work items (parent/child) ─────────────────────────────────────────

def test_create_child_nests_and_derives_parent(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    # folder nests inside the parent's folder
    assert (root / "docs/work/backlog" / p.slug / c.slug / "state.yaml").is_file()
    got = st.get(c.slug)
    assert got.parent == p.slug
    assert got.status == "backlog"                  # inherits parent's status folder
    assert st.get(p.slug).parent == ""              # top-level


def test_create_child_unknown_parent_errors(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    with pytest.raises(ValueError):
        st.create("Orphan", created="2026-01-01", parent="no-such-slug")


def test_discovery_is_depth_agnostic(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    assert st.path(c.slug) == root / "docs/work/backlog" / p.slug / c.slug
    assert {i.slug for i in st.query()} == {p.slug, c.slug}      # query walks
    assert {i.slug for i in st.query(status="backlog")} == {p.slug, c.slug}


def test_parent_transition_carries_children(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    st.start(p.slug)                                # git mv of the parent folder
    assert st.get(p.slug).status == "active"
    child = st.get(c.slug)
    assert child.status == "active"                 # rode along, still nested
    assert child.parent == p.slug
    assert (root / "docs/work/active" / p.slug / c.slug / "state.yaml").is_file()


def test_child_transition_denests_to_top_level(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    st.start(c.slug)                                # child moves to a new status alone
    child = st.get(c.slug)
    assert child.status == "active"
    assert child.parent == ""                       # de-nested (relation ends with nesting)
    assert (root / "docs/work/active" / c.slug / "state.yaml").is_file()
    assert st.get(p.slug).status == "backlog"       # parent unaffected


def test_drop_parent_removes_children(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    p = st.create("Parent", created="2026-01-01")
    c = st.create("Child", created="2026-01-02", parent=p.slug)
    st.drop(p.slug)
    assert st.get(p.slug) is None
    assert st.get(c.slug) is None                   # nested child went with it


def test_cli_new_parent_and_list_nesting(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    p = st.create("Parent", created="2026-01-01")
    assert main(["work", "new", "Child task", "--parent", p.slug]) == 0
    child_slug = capsys.readouterr().out.strip()
    assert FsWorkStore.open(root).get(child_slug).parent == p.slug
    assert main(["work", "list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    parent_line = next(ln for ln in lines if ln.startswith(p.slug))
    child_line = next(ln for ln in lines if child_slug in ln)
    assert child_line.startswith("  ")              # child indented under parent
    assert lines.index(parent_line) < lines.index(child_line)


def test_cli_new_unknown_parent_errors(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "new", "X", "--parent", "nope"]) == 1
