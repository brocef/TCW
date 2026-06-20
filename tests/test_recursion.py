"""Cross-node recursion layer (work Spec 2): topology, epics, reconcile,
the inbox channel, and worktrees. pytest over nested tmp_path git repos."""

import subprocess
from pathlib import Path

import pytest

# Imports grow per task — start with Task 1's, add each task's symbols when you
# write that task's test (Task 3: reconcile; Task 4: delegate, escalate;
# Task 5: add_worktree, ensure_worktree_ignored, git_commit, remove_worktree).
from tcw.store.fs import FsWorkStore, child_nodes, init, parent_node


def mk_node(base: Path, name: str) -> Path:
    """A git repo with docs/work/ initialized, at base/name."""
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


def commit_all(root: Path, msg: str = "init") -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", msg], check=True)


# ── Task 1: topology ─────────────────────────────────────────────────────────

def test_child_nodes_finds_children_excludes_own_worktree_keeps_nested_repo(tmp_path):
    parent = mk_node(tmp_path, "parent")
    subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)   # commit parent's
    subprocess.run(["git", "-C", str(parent), "commit", "-qm", "init"], check=True)  # OWN files
    child = mk_node(parent, "child")                       # direct child node
    deep = mk_node(parent / "group", "deep")              # under a non-node folder
    plain_repo = parent / "lib"                            # a git repo WITHOUT docs/work
    plain_repo.mkdir()
    subprocess.run(["git", "init", "-q", str(plain_repo)], check=True)
    # NB: never `git add -A` the parent now — it holds uncommitted nested repos
    # (child/deep/lib) and git would abort ("does not have a commit checked out").
    subprocess.run(["git", "-C", str(parent), "worktree", "add", "-q",
                    "-b", "work/x", str(parent / ".worktrees" / "x")], check=True)

    found = {p.resolve() for p in child_nodes(parent)}
    assert child.resolve() in found
    assert deep.resolve() in found                         # skips intermediate non-node folder
    assert (parent / ".worktrees" / "x").resolve() not in found   # own worktree excluded
    assert plain_repo.resolve() not in found               # repo without docs/work is not a node


def test_parent_node(tmp_path):
    parent = mk_node(tmp_path, "parent")
    child = mk_node(parent, "child")
    assert parent_node(child).resolve() == parent.resolve()
    assert parent_node(parent) is None                     # root has no parent node


# ── Task 2: epic / initiative fields ─────────────────────────────────────────

def test_new_epic_and_initiative_fields(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path, "repo")
    monkeypatch.chdir(root)
    from tcw.cli import main
    assert main(["work", "new", "Build it", "--epic", "--initiative", "2026-01-01-epic"]) == 0
    slug = capsys.readouterr().out.strip()
    item = FsWorkStore.open(root).get(slug)
    assert item.type == "epic"
    assert item.initiative == "2026-01-01-epic"


def test_edit_sets_and_clears_initiative(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path, "repo"))
    item = st.create("Task", created="2026-01-01")
    st.set_field(item.slug, "initiative", "2026-01-01-epic")
    assert st.get(item.slug).initiative == "2026-01-01-epic"
    st.set_field(item.slug, "initiative", "")
    assert st.get(item.slug).initiative == ""
