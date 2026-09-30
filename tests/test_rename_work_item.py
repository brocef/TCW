"""`tcw work rename` gives an open item a new slug, rewrites what names it, and
leaves the old slug resolving (spec: 2026-09-29-add-a-way-to-rename-a-work-item-s-slug)."""

import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import FsWorkStore, init

from test_recursion import commit_all, mk_node

OLD = "2026-01-01-remove-a-participant"
NEW = "2026-01-01-add-remove-or-step-down"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True).stdout


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = mk_node(tmp_path, name)
    commit_all(root)
    return root


def item(root: Path, title: str, **fields) -> str:
    st = FsWorkStore.open(root)
    blocked_by = fields.pop("blocked_by", None)
    slug = st.create_work(title, created="2026-01-01", **fields).item.slug
    if blocked_by:
        st.set_field(slug, "blocked_by", blocked_by)
    settle(root, f"add {slug}")
    return slug


def settle(root: Path, msg: str) -> None:
    """Commit whatever is there, if anything."""
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "--allow-empty", "-m", msg],
                   check=True)


def rename(root: Path, monkeypatch, capsys, *args: str) -> tuple[int, str, str]:
    monkeypatch.chdir(root)
    code = main(["work", "rename", *args])
    out = capsys.readouterr()
    return code, out.out, out.err


def state(root: Path, slug: str) -> dict:
    return yaml.safe_load((FsWorkStore.open(root).path(slug) / "state.yaml").read_text())


# ── 1: the move and the record ───────────────────────────────────────────────

def test_a_backlog_item_is_renamed_in_one_commit(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    assert item(root, "Remove a participant") == OLD
    before = state(root, OLD)
    code, out, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 0, err
    assert (root / "docs/work/backlog" / NEW).is_dir()
    assert not (root / "docs/work/backlog" / OLD).exists()
    assert state(root, NEW) == before
    assert git(root, "log", "-1", "--format=%s").strip() == f"tcw work: rename {OLD} → {NEW}"
    assert yaml.safe_load((root / "docs/work/renames.yaml").read_text()) == {OLD: NEW}
    assert git(root, "status", "--porcelain").strip() == ""


# ── 2: references on this board ──────────────────────────────────────────────

def test_blockers_parents_and_initiatives_follow(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    epic = item(root, "Remove a participant", type="epic")
    blocked = item(root, "Blocked thing", blocked_by=[{"slug": epic}])
    slice_ = item(root, "A slice", initiative=epic)
    code, _, err = rename(root, monkeypatch, capsys, epic, "add-remove-or-step-down")
    assert code == 0, err
    assert state(root, blocked)["blocked_by"] == [{"slug": NEW}]
    assert state(root, slice_)["initiative"] == NEW
    changed = git(root, "show", "--name-only", "--format=", "HEAD")
    assert f"{blocked}/state.yaml" in changed and f"{slice_}/state.yaml" in changed


# ── 3: reads follow, writes refuse ───────────────────────────────────────────

def test_show_follows_and_start_refuses(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    assert main(["work", "show", OLD]) == 0
    out = capsys.readouterr()
    assert NEW in out.out and f"{OLD} was renamed to {NEW}" in out.err
    assert main(["work", "start", OLD]) == 1
    assert f"use the new slug" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(NEW).status == "backlog"


# ── 4: a blocker in another project ──────────────────────────────────────────

def test_a_blocker_in_another_project_follows_the_rename(tmp_path, monkeypatch, capsys):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)
    commit_all(parent)
    assert item(child, "Remove a participant") == OLD
    waiting = item(parent, "Waiting", blocked_by=[{"external": f"child/{OLD}"}])
    assert rename(child, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0

    board = FsWorkStore.open(parent)
    assert board.unresolved_blockers(board.get(waiting)) != []      # still open
    renamed = FsWorkStore.open(child)
    renamed.start(NEW)
    renamed.complete(NEW, "done", [])
    assert board.unresolved_blockers(board.get(waiting)) == []      # followed to done


# ── 5: the old slug is never handed out again ────────────────────────────────

def test_a_new_item_does_not_take_the_old_slug(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    assert item(root, "Remove a participant") == f"{OLD}-2"


# ── 6: refusals ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("setup, new, says", [
    ("worktree", "add-remove-or-step-down", "worktree"),
    ("owner", "add-remove-or-step-down", "held by"),
    ("completed", "add-remove-or-step-down", "only an open item"),
    ("taken", "taken", "already taken"),
    ("plain", "Add Remove", "not a slug"),
    ("plain", "2026-02-02-other-day", "different date"),
])
def test_refusals_change_nothing(tmp_path, monkeypatch, capsys, setup, new, says):
    root = node(tmp_path)
    item(root, "Remove a participant")
    st = FsWorkStore.open(root)
    if setup == "worktree":
        st.set_field(OLD, "worktree", f".worktrees/{OLD}")
        st.set_field(OLD, "branch", f"work/{OLD}")
    elif setup == "owner":
        st.start(OLD, owner="someone-else")
    elif setup == "completed":
        st.start(OLD, owner="x")
        st.complete(OLD, "done", [])
    elif setup == "taken":
        item(root, "Taken")
    settle(root, "setup")
    head = git(root, "rev-parse", "HEAD")
    monkeypatch.setenv("TCW_WORK_OWNER", "me")
    code, _, err = rename(root, monkeypatch, capsys, OLD, new)
    assert code == 1
    assert says in err, err
    assert git(root, "rev-parse", "HEAD") == head
    assert not (root / "docs/work/renames.yaml").exists()


# ── 7: an epic's children on another board, and its graveyard entries ────────

def test_an_epics_children_elsewhere_and_its_resolved_ones_follow(
        tmp_path, monkeypatch, capsys):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)
    commit_all(parent)
    st = FsWorkStore.open(parent)
    epic = item(parent, "Remove a participant", type="epic")
    st.start(epic, owner="x")
    here = item(parent, "Done here", initiative=epic)
    st.start(here, owner="x")
    st.complete(here, "done", [])
    far = item(child, "Over there", initiative=f"parent/{epic}")
    settle(parent, "resolved one")
    monkeypatch.setenv("TCW_WORK_OWNER", "x")

    assert rename(parent, monkeypatch, capsys, epic, "add-remove-or-step-down")[0] == 0

    assert state(child, far)["initiative"] == f"parent/{NEW}"
    assert git(child, "status", "--porcelain").strip() == ""        # committed there
    graveyard = yaml.safe_load((parent / "docs/work/graveyard.yaml").read_text())
    if here in graveyard:                           # retained items keep no record
        assert graveyard[here].get("initiative") in (None, NEW)
    children = {i.slug for i in FsWorkStore.open(parent).initiative_children(NEW)}
    assert far in children


# ── 8: a capability's planning doc ───────────────────────────────────────────

def test_a_capabilitys_planning_doc_is_rewritten(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    init(["capabilities"], root, "repo")
    meta = root / "docs/capabilities/remove-a-participant/meta.yaml"
    meta.parent.mkdir(parents=True)
    meta.write_text(f"Status: Missing\nPlanning doc: {OLD}\n")
    settle(root, "cap")
    item(root, "Remove a participant")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    assert f"Planning doc: {NEW}" in meta.read_text()
    assert git(root, "status", "--porcelain").strip() == ""


# ── review follow-ups ────────────────────────────────────────────────────────

def test_a_blocker_elsewhere_clears_when_the_renamed_item_resolves_in_another_clone(
        tmp_path, monkeypatch, capsys):
    """Resolved folders are not shared, so another clone only has the graveyard
    record — written under the new slug."""
    import shutil
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)
    commit_all(parent)
    item(child, "Remove a participant")
    waiting = item(parent, "Waiting", blocked_by=[{"external": f"child/{OLD}"}])
    monkeypatch.setenv("TCW_WORK_OWNER", "x")
    assert rename(child, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    renamed = FsWorkStore.open(child)
    renamed.start(NEW, owner="x")
    renamed.complete(NEW, "done", [])
    shutil.rmtree(renamed.root / "completed" / NEW, ignore_errors=True)   # another clone
    board = FsWorkStore.open(parent)
    assert board.unresolved_blockers(board.get(waiting)) == []


def test_a_bare_blocker_the_rename_did_not_rewrite_still_follows(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    other = item(root, "Other")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    st = FsWorkStore.open(root)
    st.set_field(other, "blocked_by", [{"slug": OLD}])          # written after the rename
    assert st.unresolved_blockers(st.get(other)) == [OLD]
    st.start(NEW, owner="x")
    st.complete(NEW, "done", [])
    shutil_rmtree = __import__("shutil").rmtree
    shutil_rmtree(st.root / "completed" / NEW, ignore_errors=True)
    assert st.unresolved_blockers(st.get(other)) == []


def test_a_graveyard_that_cannot_be_read_refuses_before_anything_moves(
        tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    blocked = item(root, "Blocked", blocked_by=[{"slug": OLD}])
    graveyard = root / "docs/work/graveyard.yaml"
    graveyard.write_text("{}\n")
    settle(root, "graveyard")
    graveyard.write_text("- not\n- a mapping\n")
    head = git(root, "rev-parse", "HEAD")
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 1 and "graveyard.yaml" in err, err
    assert git(root, "rev-parse", "HEAD") == head
    assert (root / "docs/work/backlog" / OLD / "state.yaml").exists()
    assert not (root / "docs/work/renames.yaml").exists()
    assert git(root, "diff", "--cached", "--name-only").strip() == ""
    assert state(root, blocked)["blocked_by"] == [{"slug": OLD}]


def test_a_failure_after_the_move_is_undone(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    blocked = item(root, "Blocked", blocked_by=[{"slug": OLD}])
    head = git(root, "rev-parse", "HEAD")

    def boom(*a, **k):
        raise ValueError("disk full")
    monkeypatch.setattr(FsWorkStore, "_apply_reference_edits", boom)
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 1 and "disk full" in err, err
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "status", "--porcelain").strip() == ""
    assert (root / "docs/work/backlog" / OLD / "state.yaml").exists()
    assert state(root, blocked)["blocked_by"] == [{"slug": OLD}]


def test_a_leftover_folder_at_the_new_name_is_refused(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    (root / "docs/work/backlog" / NEW).mkdir()
    (root / "docs/work/backlog" / NEW / ".DS_Store").write_text("")
    head = git(root, "rev-parse", "HEAD")
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 1 and "already exists" in err, err
    assert git(root, "rev-parse", "HEAD") == head
    assert (root / "docs/work/backlog" / OLD / "state.yaml").exists()


def test_uncommitted_edits_in_the_item_are_refused(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    (root / "docs/work/backlog" / OLD / "spec.md").write_text("# half written\n")
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 1 and "uncommitted" in err, err
    assert not (root / "docs/work/renames.yaml").exists()


def test_a_tcw_link_to_the_old_slug_still_validates(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    other = item(root, "Other")
    (FsWorkStore.open(root).path(other) / "notes.md").write_text(
        f"See [the item](tcw://W/{OLD}).\n")
    settle(root, "link")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    assert main(["validate"]) == 0, capsys.readouterr()


def test_a_bound_ticket_is_named(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    (root / "docs/work/backlog" / OLD / "tracker.yaml").write_text(
        'schema: 1\nprovider: jira-cloud\nproject: probe\npart: default\n'
        'ticket:\n    id: "10052"\n    key: TCWCLAIM-6\n'
        '    url: https://example.invalid/browse/TCWCLAIM-6\n'
        'bound: "2026-09-14"\nunlinked: []\n')
    settle(root, "bind")
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 0, err
    assert "TCWCLAIM-6" in err, err


def test_path_follows_and_validate_reports_a_loop(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    assert main(["work", "path", OLD]) == 0
    assert NEW in capsys.readouterr().out
    (root / "docs/work/renames.yaml").write_text(
        f"{OLD}: {NEW}\n2026-01-01-x: 2026-01-01-y\n2026-01-01-y: 2026-01-01-x\n")
    assert main(["validate"]) == 1
    out = capsys.readouterr()
    assert "loop" in (out.out + out.err), out


def test_an_epics_resolved_child_still_counts(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    epic = item(root, "Remove a participant", type="epic")
    st = FsWorkStore.open(root)
    st.start(epic, owner="x")
    done = item(root, "Done", initiative=epic)
    st.start(done, owner="x")
    st.complete(done, "done", [])
    settle(root, "resolved child")
    monkeypatch.setenv("TCW_WORK_OWNER", "x")
    assert rename(root, monkeypatch, capsys, epic, "add-remove-or-step-down")[0] == 0
    graveyard = yaml.safe_load((root / "docs/work/graveyard.yaml").read_text()) or {}
    live = {i.slug for i in FsWorkStore.open(root).initiative_children(NEW)}
    assert done in live or graveyard.get(done, {}).get("initiative") == NEW


def test_a_dirty_graveyard_the_rename_does_not_touch_is_left_out(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    item(root, "Remove a participant")
    graveyard = root / "docs/work/graveyard.yaml"
    graveyard.write_text("{}\n")
    settle(root, "graveyard")
    graveyard.write_text("{}\n# someone's edit\n")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    assert "graveyard.yaml" not in git(root, "show", "--name-only", "--format=", "HEAD")
    assert "someone's edit" in graveyard.read_text()


def test_a_dirty_graveyard_the_rename_must_rewrite_refuses(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    graveyard = root / "docs/work/graveyard.yaml"
    graveyard.write_text(yaml.safe_dump({"2026-01-01-done": {
        "resolution": "done", "resolved": "2026-01-02", "initiative": OLD}}))
    settle(root, "graveyard")
    item(root, "Remove a participant", type="epic")
    graveyard.write_text(graveyard.read_text() + "# someone's edit\n")
    head = git(root, "rev-parse", "HEAD")
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    assert code == 1 and "uncommitted" in err, err
    assert git(root, "rev-parse", "HEAD") == head
    assert not (root / "docs/work/renames.yaml").exists()


def test_tombstone_is_still_abstract_and_renamed_is_not():
    from tcw.store.base import WorkStore
    assert "tombstone" in WorkStore.__abstractmethods__
    assert "renamed" not in WorkStore.__abstractmethods__


def test_an_unqualified_external_blocker_follows_to_the_resolved_record(
        tmp_path, monkeypatch, capsys):
    import shutil
    root = node(tmp_path)
    item(root, "Remove a participant")
    other = item(root, "Other")
    assert rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")[0] == 0
    st = FsWorkStore.open(root)
    st.set_field(other, "blocked_by", [{"external": OLD}])
    st.start(NEW, owner="x")
    st.complete(NEW, "done", [])
    shutil.rmtree(st.root / "completed" / NEW, ignore_errors=True)   # another clone
    assert st.unresolved_blockers(st.get(other)) == []


def test_an_undo_that_cannot_run_git_still_moves_the_folder_back(tmp_path, monkeypatch, capsys):
    """Another git process holding the index mid-rename: the folder still goes
    back, and the error says what was left."""
    root = node(tmp_path)
    item(root, "Remove a participant")
    lock = root / ".git" / "index.lock"

    def boom(*a, **k):
        lock.write_text("")                         # git is busy from here on
        raise ValueError("disk full")
    monkeypatch.setattr(FsWorkStore, "_apply_reference_edits", boom)
    code, _, err = rename(root, monkeypatch, capsys, OLD, "add-remove-or-step-down")
    lock.unlink()
    assert code == 1 and "disk full" in err, err
    assert (root / "docs/work/backlog" / OLD / "state.yaml").exists()
    assert not (root / "docs/work/backlog" / NEW).exists()
    assert "undone except for" in err, err


def test_a_childs_parent_and_a_nested_childs_folder_follow(tmp_path, monkeypatch, capsys):
    root = node(tmp_path)
    parent = item(root, "Remove a participant")
    child = item(root, "A child", parent=parent)
    nested = root / "docs/work/backlog" / parent / "2026-01-01-nested"
    nested.mkdir()
    (nested / "state.yaml").write_text(f"title: Nested\nstatus: backlog\ncreated: '2026-01-01'\nparent: {parent}\n")
    settle(root, "nested")
    assert rename(root, monkeypatch, capsys, parent, "add-remove-or-step-down")[0] == 0
    assert state(root, child)["parent"] == NEW
    moved = root / "docs/work/backlog" / NEW / "2026-01-01-nested" / "state.yaml"
    assert yaml.safe_load(moved.read_text())["parent"] == NEW
    assert git(root, "status", "--porcelain").strip() == ""


def test_a_dirty_child_on_another_board_is_left_and_named(tmp_path, monkeypatch, capsys):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    commit_all(child)
    commit_all(parent)
    epic = item(parent, "Remove a participant", type="epic")
    far = item(child, "Over there", initiative=f"parent/{epic}")
    far_state = FsWorkStore.open(child).path(far) / "state.yaml"
    far_state.write_text(far_state.read_text() + "# unsaved\n")
    code, _, err = rename(parent, monkeypatch, capsys, epic, "add-remove-or-step-down")
    assert code == 0, err
    assert "uncommitted" in err and far in err, err
    assert "# unsaved" in far_state.read_text()
    assert yaml.safe_load(far_state.read_text())["initiative"] == f"parent/{epic}"
