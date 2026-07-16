import subprocess
from pathlib import Path

import pytest

from tcw.store.base import WORK_ARTIFACTS, WORK_STATUSES, IllegalTransition, MultipleMatch, topo_order
from tcw.store.fs import FsWorkStore, init


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


def subnode(parent: Path, rel: str) -> Path:
    """A same-repo subdir node: sentinel + docs/work, NO separate git init — the
    layout descendant_nodes (unlike git-root-based child_nodes) is meant to find."""
    d = parent / rel
    d.mkdir(parents=True)
    init(["work"], d)
    return d


# ── init / slug ──────────────────────────────────────────────────────────────

def test_init_gitkeep_persistence(tmp_path):
    root = node(tmp_path)
    for s in ("inbox", "backlog", "active", "completed"):
        assert (root / "docs" / "work" / s / ".gitkeep").is_file()
    assert not (root / "docs" / "work" / "blocked").exists()


def test_formal_work_statuses_exclude_raw_inbox():
    assert WORK_STATUSES == ("backlog", "active", "completed")


def test_raw_inbox_state_yaml_is_not_discovered_as_work(tmp_path):
    root = node(tmp_path)
    raw = root / "docs/work/inbox/request"
    raw.mkdir()
    (raw / "state.yaml").write_text("title: not formal\n")
    assert FsWorkStore.open(root).query() == []


def test_slug_generation_collision_and_immutability(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    a = st.create("Fix the bug", created="2026-01-01")
    assert a.slug == "2026-01-01-fix-the-bug"
    b = st.create("Fix the bug", created="2026-01-01")
    assert b.slug == "2026-01-01-fix-the-bug-2"        # collision suffix
    st.set_field(a.slug, "title", "Renamed")           # title drifts...
    assert st.get(a.slug).title == "Renamed"
    assert st.get(a.slug).slug == a.slug               # ...slug is frozen


def test_body_path_points_at_initial_request_md(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    item = st.create("Task", created="2026-01-01")
    body = st.body_path(item.slug)
    assert body == st.path(item.slug) / "initial-request.md"
    assert body.exists()
    assert st.body_path("no-such-slug") is None


# ── raw inbox intake ─────────────────────────────────────────────────────────

def test_inbox_list_and_show_standalone_text(tmp_path):
    root = node(tmp_path)
    source = root / "docs/work/inbox/request.txt"
    source.write_text("please fix it\n", encoding="utf-8")
    st = FsWorkStore.open(root)
    assert [(e.ref, e.title, e.kind) for e in st.inbox_list()] == [
        ("request.txt", "request", "file")]
    detail = st.inbox_show("request.txt")
    assert detail.body == "please fix it\n"
    assert detail.resources[0].name == "request.txt"
    assert detail.resources[0].readable is True


def test_inbox_accept_folder_generates_request_and_attachments(tmp_path):
    root = node(tmp_path)
    entry = root / "docs/work/inbox/big-request"
    (entry / "nested").mkdir(parents=True)
    (entry / "INDEX.md").write_text("Original request\n", encoding="utf-8")
    (entry / "asset.bin").write_bytes(b"\0\1")
    (entry / "nested/notes.txt").write_text("notes\n", encoding="utf-8")
    (entry / ".ignored").write_text("nope", encoding="utf-8")
    (entry / "link").symlink_to(entry / "asset.bin")
    st = FsWorkStore.open(root)
    item = st.inbox_accept("big-request", title="Accepted title")
    assert item.status == "backlog"
    assert item.title == "Accepted title"
    assert not entry.exists()
    created = st.path(item.slug)
    assert (created / "attachments/asset.bin").read_bytes() == b"\0\1"
    assert (created / "attachments/nested/notes.txt").read_text() == "notes\n"
    assert not (created / "attachments/.ignored").exists()
    body = (created / "initial-request.md").read_text()
    assert "- `initial-request.md` — accepted from `INDEX.md`" in body
    assert "- `attachments/asset.bin`" in body
    assert "- `attachments/nested/notes.txt`" in body
    assert body.endswith("Original request\n")


def test_inbox_accept_binary_file_does_not_render_binary(tmp_path):
    root = node(tmp_path)
    source = root / "docs/work/inbox/sample.dat"
    source.write_bytes(b"\0secret")
    st = FsWorkStore.open(root)
    assert st.inbox_show("sample.dat").body is None
    item = st.inbox_accept("sample.dat")
    created = st.path(item.slug)
    assert (created / "attachments/sample.dat").read_bytes() == b"\0secret"
    assert "secret" not in (created / "initial-request.md").read_text()


@pytest.mark.parametrize("indexes", [("INDEX.md",), ("INDEX.txt",)])
def test_inbox_accept_folder_requires_one_index(tmp_path, indexes):
    root = node(tmp_path)
    entry = root / "docs/work/inbox/request"
    entry.mkdir()
    for name in indexes:
        (entry / name).write_text("body", encoding="utf-8")
    st = FsWorkStore.open(root)
    if len(indexes) == 1:
        assert st.inbox_accept("request").status == "backlog"


def test_inbox_accept_folder_rejects_missing_or_ambiguous_index_without_consuming(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    missing = root / "docs/work/inbox/missing"
    missing.mkdir()
    with pytest.raises(ValueError, match="requires"):
        st.inbox_accept("missing")
    assert missing.exists() and st.query() == []
    ambiguous = root / "docs/work/inbox/ambiguous"
    ambiguous.mkdir()
    (ambiguous / "INDEX.md").write_text("one")
    (ambiguous / "INDEX.txt").write_text("two")
    with pytest.raises(ValueError, match="both"):
        st.inbox_accept("ambiguous")
    assert ambiguous.exists() and st.query() == []


def test_cli_inbox_list_show_accept(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    (root / "docs/work/inbox/request.md").write_text("Do the thing\n")
    monkeypatch.chdir(root)
    assert main(["work", "inbox", "list"]) == 0
    assert "request.md | file | request" in capsys.readouterr().out
    assert main(["work", "inbox", "show", "request.md"]) == 0
    shown = capsys.readouterr().out
    assert "Do the thing" in shown and "request.md" in shown
    assert main(["work", "inbox", "accept", "request.md", "--title", "Chosen"]) == 0
    slug = capsys.readouterr().out.strip()
    assert FsWorkStore.open(root).get(slug).title == "Chosen"


def test_artifacts_report_bounded_presence_and_locator(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")
    d = st.path(item.slug)
    (d / "initial-request.md").write_text("request\n", encoding="utf-8")
    (d / "spec.md").write_text("   \n", encoding="utf-8")
    (d / "plan.md").write_text("plan\n", encoding="utf-8")

    artifacts = {a.name: a.present for a in st.artifacts(item.slug)}
    assert tuple(artifacts) == WORK_ARTIFACTS
    assert artifacts == {
        "initial-request": True,
        "spec": False,
        "plan": True,
        "outcome": False,
        "refined-outcome": False,
    }
    assert st.artifact_locator(item.slug, "plan") == str(d / "plan.md")
    assert st.artifact_locator(item.slug, "../plan") is None
    assert st.artifact_locator("no-such-slug", "plan") is None


def test_multiple_match_resolution_error(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    for s in ("active", "backlog"):
        d = root / "docs/work" / s / "dup"
        d.mkdir()
        (d / "state.yaml").write_text("slug: dup\n")     # state.yaml is the item marker
    with pytest.raises(MultipleMatch):
        st.get("dup")


def test_cli_path_prints_current_item_folder(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Task", created="2026-01-01")

    assert main(["work", "path", item.slug]) == 0
    assert capsys.readouterr().out.strip() == str(root / "docs/work/backlog" / item.slug)

    st.start(item.slug)
    assert main(["work", "path", item.slug]) == 0
    assert capsys.readouterr().out.strip() == str(root / "docs/work/active" / item.slug)


def test_cli_path_missing_slug_errors(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "path", "no-such-slug"]) == 1
    out = capsys.readouterr()
    assert out.out == ""
    assert "tcw work path: no such work item: no-such-slug" in out.err


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


def test_drop_only_from_backlog(tmp_path):
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


# ── capabilities gate at complete (DoD teeth) ────────────────────────────────

def _wc_node(tmp_path: Path) -> Path:
    """A node with both work and capabilities trees."""
    root = node(tmp_path)
    init(["capabilities"], root)
    return root


def _item_with_delta(root: Path, sidecar: str) -> str:
    """Create + start a work item carrying a capabilities.yaml sidecar."""
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    from tcw.cli import main
    main(["work", "start", slug])
    (root / "docs" / "work" / "active" / slug / "capabilities.yaml").write_text(sidecar)
    return slug


def test_complete_gate_blocks_unreconciled_new(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    err = capsys.readouterr().err
    assert "auth/login" in err and "Missing" in err
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_complete_gate_passes_when_reconciled(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    FsCapabilitiesStore.open(root).set("auth/login", {"Status": "Supported"})
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_gate_force_overrides(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done",
                 "--confirm", "--force"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_complete_gate_omitted_passes(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    FsCapabilitiesStore.open(root).set("auth/login", {"Status": "Omitted"})
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_changed_missing_passes(tmp_path, monkeypatch, capsys):
    """A changed: entry only fails if it doesn't resolve — a still-Missing one
    that resolves passes (routine body/wording edits leave status alone)."""
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    slug = _item_with_delta(root, "changed:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_unresolved_refuses(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    slug = _item_with_delta(root, "new:\n- ghost/nope\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    assert "does not resolve" in capsys.readouterr().err


def test_complete_gate_unparseable_sidecar_refuses(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    slug = _item_with_delta(root, "new: [unterminated\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    assert "unreadable" in capsys.readouterr().err


def test_complete_gate_no_sidecar_unaffected(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = _wc_node(tmp_path)
    monkeypatch.chdir(root)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    main(["work", "start", slug])
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_work_only_node_unaffected(tmp_path, monkeypatch, capsys):
    """A node with no capabilities tree has nothing to reconcile."""
    from tcw.cli import main
    root = node(tmp_path)                      # work only, no capabilities
    monkeypatch.chdir(root)
    slug = _item_with_delta(root, "new:\n- auth/login\n")
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0


def test_complete_gate_reads_after_worktree_mergeback(tmp_path, monkeypatch, capsys):
    """The reconciling flip happens on the worktree branch; the primary tree still
    reads Missing until merge-back. The gate must pass because it runs AFTER
    merge_worktree — a pre-merge gate would false-fail here."""
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _git_subnode(tmp_path, "repo")
    init(["capabilities"], root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed cap"], check=True)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    (root / "docs" / "work" / "backlog" / slug / "capabilities.yaml").write_text(
        "new:\n- auth/login\n")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "declare"], check=True)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    # Flip on the worktree branch only, and commit there.
    wt = root / ".worktrees" / slug
    FsCapabilitiesStore.open(wt).set("auth/login", {"Status": "Supported"})
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-am", "flip on branch"],
                   check=True)
    # Primary tree still Missing until merge-back.
    assert FsCapabilitiesStore.open(root).get("auth/login").status == "Missing"

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(root).get(slug).status == "completed"
    assert FsCapabilitiesStore.open(root).get("auth/login").status == "Supported"


def test_complete_gate_catches_declaration_added_on_branch(tmp_path, monkeypatch, capsys):
    """A `new:` declaration added ON the worktree branch and left Missing must be
    caught — the gate must read the declared list from the merged tree, not the
    pre-merge snapshot."""
    from tcw.cli import main
    from tcw.store.fs import FsCapabilitiesStore
    root = _git_subnode(tmp_path, "repo")
    init(["capabilities"], root)
    FsCapabilitiesStore.open(root).add("auth/login", name="Login", status="Missing")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"], check=True)
    slug = FsWorkStore.open(root).create("Task", created="2026-01-01").slug
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "item"], check=True)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    # Declare the delta ON the branch (not present in the primary snapshot), leave Missing.
    wt = root / ".worktrees" / slug
    (wt / "docs" / "work" / "active" / slug / "capabilities.yaml").write_text(
        "new:\n- auth/login\n")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "declare on branch"],
                   check=True)

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm"]) == 1
    assert "auth/login" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "active"


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
    # row: slug | status | lifecycle-stages | priority | title
    assert rows[hot.slug][3] == "7"
    assert rows[cold.slug][3] == "-"
    assert rows[hot.slug][4] == "Hot"                     # title still follows


def test_cli_list_shows_lifecycle_stage_letters(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Planned", created="2026-01-01")
    d = st.path(item.slug)
    (d / "initial-request.md").write_text("request\n", encoding="utf-8")
    (d / "spec.md").write_text("spec\n", encoding="utf-8")
    (d / "plan.md").write_text("plan\n", encoding="utf-8")

    assert main(["work", "list"]) == 0
    row = capsys.readouterr().out.strip().split(" | ")
    assert row[2] == "RSP"


def test_cli_list_ignores_empty_lifecycle_artifacts(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Sketch", created="2026-01-01")
    d = st.path(item.slug)
    (d / "initial-request.md").write_text("   \n", encoding="utf-8")
    (d / "spec.md").write_text("spec\n", encoding="utf-8")

    assert main(["work", "list"]) == 0
    row = capsys.readouterr().out.strip().split(" | ")
    assert row[2] == "S"


def test_cli_list_shows_outcome_and_refined_outcome_stages(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    item = st.create("Finished", created="2026-01-01")
    d = st.path(item.slug)
    (d / "outcome.md").write_text("outcome\n", encoding="utf-8")
    (d / "refined-outcome.md").write_text("refined\n", encoding="utf-8")

    assert main(["work", "list"]) == 0
    row = capsys.readouterr().out.strip().split(" | ")
    assert row[2] == "ROF"


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


# ── effort / complexity ──────────────────────────────────────────────────────

def test_effort_complexity_persist_and_read_back(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    assert main(["work", "new", "A", "--effort", "high", "--complexity", "low"]) == 0
    a = st.query(status="backlog")[0]
    assert (a.effort, a.complexity) == ("high", "low")
    # persisted as real state.yaml keys
    import yaml
    state = yaml.safe_load((st.path(a.slug) / "state.yaml").read_text())
    assert state["effort"] == "high" and state["complexity"] == "low"


def test_edit_effort_leaves_complexity_untouched(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    st.set_field(a.slug, "complexity", "high")
    assert main(["work", "edit", a.slug, "--effort", "medium"]) == 0
    got = FsWorkStore.open(root).get(a.slug)
    assert (got.effort, got.complexity) == ("medium", "high")   # complexity preserved


def test_show_displays_when_set_omits_when_unset(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")
    assert main(["work", "show", a.slug]) == 0
    assert "effort:" not in capsys.readouterr().out          # omitted when unset
    st.set_field(a.slug, "effort", "very-high")
    assert main(["work", "show", a.slug]) == 0
    assert "effort: very-high" in capsys.readouterr().out


def test_invalid_effort_rejected_and_no_write(tmp_path, monkeypatch):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    with pytest.raises(SystemExit):                           # argparse choices=
        main(["work", "new", "A", "--effort", "bogus"])
    assert FsWorkStore.open(root).query(status="backlog") == []   # nothing created


def test_missing_and_null_keys_read_as_empty(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    a = st.create("A", created="2026-01-01")                 # no effort/complexity keys
    assert (st.get(a.slug).effort, st.get(a.slug).complexity) == ("", "")
    st.set_field(a.slug, "effort", None)                     # bare YAML `effort:` (null)
    assert FsWorkStore.open(root).get(a.slug).effort == ""   # `or ""` coercion


# ── list --include-descendants ───────────────────────────────────────────────

def test_list_include_descendants_groups_by_node(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    FsWorkStore.open(subnode(root, "Project-A")).create("A feature", created="2026-01-01")
    FsWorkStore.open(subnode(root, "Project-B")).create("B feature", created="2026-01-01")
    (root / "plain-subdir").mkdir()                          # no sentinel → not a node

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out

    # root-first, then path-sorted; a non-node subdir is never a group
    assert out.index("# .\n") < out.index("# ./Project-A") < out.index("# ./Project-B")
    assert "plain-subdir" not in out
    # each node's item shows under its own header (node-bounded boards)
    assert out.index("2026-01-01-a-feature") < out.index("# ./Project-B")
    assert "2026-01-01-b-feature" in out.split("# ./Project-B", 1)[1]
    assert "2026-01-01-root-thing" in out.split("# ./Project-A", 1)[0]


def test_list_include_descendants_skips_own_worktree(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    subnode(root, ".worktrees/some-item")                   # a --worktree checkout copies the sentinel

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    assert ".worktrees" not in capsys.readouterr().out


def test_list_include_descendants_nested(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(subnode(root, "Project-A/Nested")).create("deep", created="2026-01-01")

    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out
    assert "# ./Project-A/Nested" in out                    # transitive: nested node is its own group
    assert "2026-01-01-deep" in out


def test_list_without_flag_has_no_node_headers(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    subnode(root, "Project-A")

    monkeypatch.chdir(root)
    assert main(["work", "list"]) == 0
    out = capsys.readouterr().out
    assert "# ." not in out and "Project-A" not in out      # descendants untouched without the flag


# ── effort/complexity level normalization ────────────────────────────────────

def test_normalize_work_level_aliases_case_and_passthrough():
    from tcw.store.base import normalize_work_level
    assert normalize_work_level("h") == "high"
    assert normalize_work_level("VH") == "very-high"
    assert normalize_work_level("L") == "low"
    assert normalize_work_level("m") == "medium"
    assert normalize_work_level("HIGH") == "high"          # canonical, case-insensitive
    assert normalize_work_level("very-high") == "very-high"


def test_normalize_work_level_rejects_unknown():
    from tcw.store.base import normalize_work_level
    with pytest.raises(ValueError, match="L/M/H/VH"):
        normalize_work_level("s")                          # T-shirt slip, not a level
    for junk in ("", "   ", "xl"):                          # empty/whitespace/unknown all rejected
        with pytest.raises(ValueError, match="invalid level"):
            normalize_work_level(junk)


def test_cli_new_effort_alias_stored_canonical(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    assert main(["work", "new", "Task", "--effort", "h", "--complexity", "vh"]) == 0
    slug = capsys.readouterr().out.strip()
    item = FsWorkStore.open(root).get(slug)
    assert item.effort == "high" and item.complexity == "very-high"


def test_cli_new_effort_invalid_exits(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit):                         # argparse rejects the bad value
        main(["work", "new", "Task", "--effort", "xl"])
    assert "L/M/H/VH" in capsys.readouterr().err


def test_cli_edit_effort_alias_stored_canonical(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    item = FsWorkStore.open(root).create("Task", created="2026-01-01")

    assert main(["work", "edit", item.slug, "--effort", "M", "--complexity", "l"]) == 0
    edited = FsWorkStore.open(root).get(item.slug)
    assert edited.effort == "medium" and edited.complexity == "low"


# ── qualified (subproject-relative) slugs ────────────────────────────────────

def _git_subnode(parent: Path, rel: str) -> Path:
    """A descendant that is its OWN committed git repo — worktree flows need a
    repo with a HEAD (a plain subnode shares the enclosing repo)."""
    d = parent / rel
    d.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "t"], check=True)
    init(["work"], d)
    subprocess.run(["git", "-C", str(d), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-q", "-m", "init"], check=True)
    return d


def test_list_include_descendants_qualifies_slugs(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    FsWorkStore.open(root).create("root thing", created="2026-01-01")
    FsWorkStore.open(subnode(root, "Project-A")).create("a feature", created="2026-01-01")
    monkeypatch.chdir(root)
    assert main(["work", "list", "--include-descendants"]) == 0
    out = capsys.readouterr().out
    assert "Project-A/2026-01-01-a-feature |" in out          # descendant slug qualified
    anchor_line = next(l for l in out.splitlines() if "root-thing" in l)
    assert anchor_line.lstrip().startswith("2026-01-01-root-thing |")  # anchor stays bare


def test_show_and_path_resolve_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "show", f"Project-A/{slug}"]) == 0
    assert slug in capsys.readouterr().out
    assert main(["work", "path", f"Project-A/{slug}"]) == 0
    out = capsys.readouterr().out.strip()
    assert out == str(sub / "docs" / "work" / "backlog" / slug)


def test_qualified_resolution_from_mid_tree_node(tmp_path, monkeypatch, capsys):
    """Anchor is wherever you invoke — a mid-tree node resolves a slug relative to
    itself, not the repo root."""
    from tcw.cli import main
    root = node(tmp_path)
    mid = subnode(root, "Project-A")
    grand = subnode(root, "Project-A/Nested")
    slug = FsWorkStore.open(grand).create("deep", created="2026-01-01").slug
    monkeypatch.chdir(mid)
    assert main(["work", "show", f"Nested/{slug}"]) == 0
    assert slug in capsys.readouterr().out


def test_start_complete_via_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "start", f"Project-A/{slug}"]) == 0
    out = capsys.readouterr()
    assert f"started Project-A/{slug}" in out.out
    assert f"complete Project-A/{slug}" in out.err            # hint echoes QUALIFIED slug
    assert FsWorkStore.open(sub).get(slug).status == "active"
    assert main(["work", "complete", f"Project-A/{slug}",
                 "--resolution", "done", "--confirm"]) == 0
    assert FsWorkStore.open(sub).get(slug).status == "completed"


def test_worktree_roundtrip_via_qualified_slug(tmp_path, monkeypatch, capsys):
    """start --worktree then complete on a descendant addressed by qualified slug:
    the worktree lands under the DESCENDANT's .worktrees/<bare> and is removed on
    complete (guards remove_worktree using bare, not the qualified slug)."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = _git_subnode(root, "Project-A")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "start", f"Project-A/{slug}", "--worktree"]) == 0
    capsys.readouterr()
    assert (sub / ".worktrees" / slug / "docs" / "work" / "active" / slug).is_dir()
    assert main(["work", "complete", f"Project-A/{slug}",
                 "--resolution", "done", "--confirm"]) == 0
    assert not (sub / ".worktrees" / slug).exists()          # torn down via bare path
    assert FsWorkStore.open(sub).get(slug).status == "completed"


def test_drop_via_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "drop", f"Project-A/{slug}"]) == 0
    assert FsWorkStore.open(sub).get(slug) is None


def test_edit_blocks_reverse_stores_bare_ref(tmp_path, monkeypatch, capsys):
    """--blocks on a qualified slug must persist a BARE ref into the other item's
    node-local blocked_by (never the qualified form)."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    s = FsWorkStore.open(sub)
    a = s.create("item a", created="2026-01-01").slug
    b = s.create("item b", created="2026-01-02").slug
    monkeypatch.chdir(root)
    assert main(["work", "edit", f"Project-A/{a}", "--blocks", b]) == 0
    blockers = [x.get("slug") for x in FsWorkStore.open(sub).get(b).blocked_by]
    assert a in blockers and f"Project-A/{a}" not in blockers


def test_bare_slug_not_found_across_nodes(tmp_path, monkeypatch, capsys):
    """Backward compat: a descendant-only slug is NOT resolvable bare from the anchor."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    monkeypatch.chdir(root)
    assert main(["work", "show", slug]) == 1                  # bare -> anchor only
    assert f"no such work item: {slug}" in capsys.readouterr().err
    assert main(["work", "show", f"Project-A/{slug}"]) == 0   # qualified resolves


def test_unresolvable_qualifier_errors_with_qualified_slug(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    assert main(["work", "show", "Nope/2026-01-01-foo"]) == 1
    assert "tcw work show: no such work item: Nope/2026-01-01-foo" in capsys.readouterr().err


def test_qualified_ambiguous_bare_surfaces_multiple_match(tmp_path, monkeypatch, capsys):
    """A qualified ref whose bare part collides inside the descendant still errors."""
    from tcw.cli import main
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    for status in ("active", "backlog"):                      # two items named 'dup'
        d = sub / "docs/work" / status / "dup"
        d.mkdir(parents=True)
        (d / "state.yaml").write_text("slug: dup\n")
    monkeypatch.chdir(root)
    assert main(["work", "show", "Project-A/dup"]) == 1
    assert "resolves to 2 items" in capsys.readouterr().err
