"""The project graph loads each node once, from its own folder — whatever case a
locator spells it in, whether its config is a symlink, and from submodules in
linked worktrees (spec:
2026-09-27-resolve-project-graph-paths-by-case-and-through-a-symlinked-config)."""

from pathlib import Path

import pytest

from test_worktree_sibling_nodes import (config, git, repo, validate,  # noqa: F401
                                         with_submodule, workspace)


def case_insensitive(where: Path) -> bool:
    (where / "probe-lower").mkdir()
    return (where / "PROBE-LOWER").exists()


def test_a_locator_in_other_letter_case_loads_the_node_once(tmp_path):
    if not case_insensitive(tmp_path):
        pytest.skip("the disk is case-sensitive")
    root = repo(tmp_path / "Root")
    spelled = str(tmp_path / "ROOT" / "kid")
    config(root, "root", children={"kid": spelled})
    config(root / "kid", "kid", parent={"root": ".."})
    done = validate(root)
    assert done.returncode == 0, done.stdout + done.stderr


def test_an_override_in_other_letter_case_is_the_node_it_names(tmp_path, monkeypatch):
    """`tcw provision` asks whether each override delivered its project; that
    check compared path text and refused what the walk had accepted."""
    if not case_insensitive(tmp_path):
        pytest.skip("the disk is case-sensitive")
    from tcw.store.project import FsProjectRegistry
    root = repo(tmp_path / "Root")
    config(root, "root", children={"kid": "kid"})
    config(root / "kid", "kid", parent={"root": ".."})
    monkeypatch.setenv("TCW_PROJECT_KID", str(tmp_path / "root" / "kid"))
    registry = FsProjectRegistry.open(root / "kid")
    assert [o.problem for o in registry.overrides()] == [None]


def test_a_symlinked_config_belongs_to_the_folder_it_sits_in(tmp_path):
    node = repo(tmp_path / "node")
    store = tmp_path / "store"
    config(store, "nd", children={"kid": "kid"})
    (node / "tcw-config.yaml").symlink_to(store / "tcw-config.yaml")
    config(node / "kid", "kid", parent={"nd": ".."})
    done = validate(node)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "not reachable" not in done.stdout + done.stderr


def test_a_submodule_node_inside_a_linked_worktree_loads_once(workspace, tmp_path):  # noqa: F811
    wt = with_submodule(workspace, tmp_path, named_by_workspace=False)
    done = validate(wt / "lib")
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_linked_worktree_of_a_submodule_repository_resolves_there(tmp_path):
    origin = repo(tmp_path / "app-origin")
    config(origin, "app-repo", parent={"workspace": ".."},
           children={"pkg-a": "pkg-a", "pkg-b": "pkg-b"})
    config(origin / "pkg-a", "pkg-a", parent={"app-repo": ".."})
    config(origin / "pkg-b", "pkg-b", parent={"app-repo": ".."})
    git(origin, "add", "-A")
    git(origin, "commit", "-qm", "nodes")
    ws = repo(tmp_path / "workspace")
    git(ws, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(origin), "app")
    config(ws, "workspace", children={"app-repo": "app"})
    git(ws, "add", "-A")
    git(ws, "commit", "-qm", "app submodule")
    git(ws / "app", "worktree", "add", "-q", "../app-wt", "-b", "feature")
    done = validate(ws / "app-wt" / "pkg-a")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "duplicate project id" not in done.stdout + done.stderr
