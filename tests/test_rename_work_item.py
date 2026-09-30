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
