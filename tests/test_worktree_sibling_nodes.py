"""In a linked worktree of a repository holding several nodes, every node of that
repository resolves to its worktree copy, not only the one the command ran from
(spec: 2026-09-15-resolve-sibling-nodes-to-their-worktree-copies; GitHub #39)."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.projectfiles import config_file, write_config, write_config_file, write_manifest


def git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    return path


def config(path: Path, pid: str, *, parent: dict | None = None,
           children: dict | None = None) -> None:
    """Write `pid`'s configuration naming its parent and children by ID, and
    put where each of them is (a path relative to `path`) in its manifest."""
    path.mkdir(parents=True, exist_ok=True)
    text = f"id: {pid}\n"
    for key, links in (("parents", parent), ("children", children)):
        if links:
            text += f"{key}:\n" + "".join(f"- {k}\n" for k in links)
    write_config(path, text)
    if parent or children:
        write_manifest(path, {**(parent or {}), **(children or {})})


def add_child(root: Path, child_id: str, location: str) -> None:
    """Add `child_id` to the end of `root`'s children, and put it at
    `location` (relative to `root`) in `root`'s manifest."""
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    document.setdefault("children", []).append(child_id)
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    write_manifest(root, {child_id: location})


def validate(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", "validate"], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


@pytest.fixture
def workspace(tmp_path) -> Path:
    """The issue's layout: an outer node whose child is the root of an inner
    repository holding two more nodes."""
    ws = repo(tmp_path / "workspace")
    config(ws, "workspace", children={"app-repo": "app"})
    app = repo(ws / "app")
    config(app, "app-repo", parent={"workspace": ".."},
           children={"pkg-a": "pkg-a", "pkg-b": "pkg-b"})
    config(app / "pkg-a", "pkg-a", parent={"app-repo": ".."})
    config(app / "pkg-b", "pkg-b", parent={"app-repo": ".."})
    git(app, "add", "-A")
    git(app, "commit", "-qm", "nodes")
    return ws


@pytest.mark.parametrize("node", ["pkg-a", "pkg-b", "."])
def test_every_node_of_a_linked_worktree_resolves_there(workspace, node):
    git(workspace / "app", "worktree", "add", "-q", "../app-wt", "-b", "feature")
    done = validate(workspace / "app-wt" / node)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "duplicate project id" not in done.stdout + done.stderr


def test_a_worktree_inside_its_own_primary_checkout(workspace):
    """TCW's own layout: `.worktrees/<slug>` under the primary checkout."""
    git(workspace / "app", "worktree", "add", "-q", ".worktrees/feature", "-b", "feature")
    done = validate(workspace / "app" / ".worktrees" / "feature" / "pkg-a")
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_node_only_the_primary_checkout_has_still_resolves_there(workspace):
    app = workspace / "app"
    git(app, "worktree", "add", "-q", "../app-wt", "-b", "feature")
    # Added on the primary checkout's branch after the worktree was made.
    config(app / "pkg-c", "pkg-c", parent={"app-repo": ".."})
    wt_cfg = config_file(workspace / "app-wt")
    wt_cfg.write_text(wt_cfg.read_text().replace(
        "- pkg-b\n", "- pkg-b\n- pkg-c\n"))
    write_manifest(workspace / "app-wt", {"pkg-c": "../app/pkg-c"})
    done = validate(workspace / "app-wt" / "pkg-a")
    assert done.returncode == 0, done.stdout + done.stderr
    from tcw.store.project import FsProjectRegistry
    # From their parent: a sibling is not in `pkg-a`'s family (TCW-108
    # Design 3.3).
    registry = FsProjectRegistry.open(workspace / "app-wt")
    where = {p.id: Path(p.locator).resolve() for p in registry.projects()}
    assert where["pkg-c"] == (app / "pkg-c").resolve()          # only main has it
    assert where["pkg-b"] == (workspace / "app-wt" / "pkg-b").resolve()
    assert registry.unreachable() == []


def test_a_nested_repository_is_not_taken_for_the_worktree_copy(workspace):
    """A separate clone at the same place in the worktree is another repository,
    not this node on the checked-out branch."""
    app = workspace / "app"
    (app / ".gitignore").write_text("vendor/\n")
    git(app, "add", ".gitignore")
    git(app, "commit", "-qm", "ignore vendor")
    config(repo(app / "vendor"), "vendor", parent={"workspace": "../.."})
    add_child(workspace, "vendor", "app/vendor")
    git(app, "worktree", "add", "-q", "../app-wt", "-b", "feature")
    config(repo(workspace / "app-wt" / "vendor"), "vendor-fork", parent={"workspace": "../.."})
    done = validate(workspace / "app-wt" / "pkg-a")
    assert done.returncode == 0, done.stdout + done.stderr
    from tcw.store.project import FsProjectRegistry
    # `vendor` is a sibling of `app-repo`, outside `pkg-a`'s family (TCW-108
    # Design 3.3), so it is looked up as a full identifier naming it would be.
    registry = FsProjectRegistry.open(workspace / "app-wt" / "pkg-a")
    assert registry.project_folder("vendor", workspace).resolve() == \
        (app / "vendor").resolve()


def with_submodule(workspace: Path, tmp_path: Path, *, named_by_workspace: bool) -> Path:
    """`app` gains a submodule node `lib`, then a linked worktree `app-wt` with the
    submodule checked out; returns the worktree. `named_by_workspace` also has
    the workspace name `app/lib`, through the primary checkout."""
    lib = repo(tmp_path / "lib-origin")
    config(lib, "lib", parent={"app-repo": ".."})
    git(lib, "add", "-A")
    git(lib, "commit", "-qm", "lib")
    app = workspace / "app"
    git(app, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "lib")
    add_child(app, "lib", "lib")
    git(app, "add", "-A")
    git(app, "commit", "-qm", "lib submodule")
    if named_by_workspace:
        add_child(workspace, "lib-too", "app/lib")
    git(app, "worktree", "add", "-q", "../app-wt", "-b", "feature")
    git(workspace / "app-wt", "-c", "protocol.file.allow=always", "submodule", "update",
        "--init", "-q")
    return workspace / "app-wt"


def test_a_submodule_of_the_repository_is_its_worktree_copy(workspace, tmp_path):
    """A submodule's checkout in the worktree is the commit this branch pins: the
    same node. Named both by the repository's root (inside the worktree) and by
    the workspace (through the primary checkout), it must load once."""
    with_submodule(workspace, tmp_path, named_by_workspace=True)
    done = validate(workspace / "app-wt" / "pkg-a")
    assert "duplicate project id 'lib'" not in done.stdout + done.stderr, \
        done.stdout + done.stderr


def test_one_id_in_two_repositories_is_still_a_duplicate(workspace):
    """Since TCW-107 an entry cannot place a project under another ID, so the
    workspace's manifest places `pkg-b` itself in a second repository, and the
    two lookups find it in two folders (Design 2.9)."""
    other = repo(workspace / "other")
    config(other, "pkg-b", parent={"workspace": ".."})
    add_child(workspace, "pkg-b", "other")
    git(workspace / "app", "worktree", "add", "-q", "../app-wt", "-b", "feature")
    from tcw.errors import ProjectGraphError
    from tcw.store.project import FsProjectRegistry
    # The workspace's children are not followed from below (TCW-108 Design
    # 3.1), so the second lookup is the one a full identifier makes.
    registry = FsProjectRegistry.open(workspace / "app-wt")
    with pytest.raises(ProjectGraphError, match="duplicate project id 'pkg-b'"):
        registry.project_folder("pkg-b", workspace)
