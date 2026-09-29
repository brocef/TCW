"""The project graph loads each node once, from its own folder — whatever case a
locator spells it in, whether its config is a symlink, and from submodules in
linked worktrees (spec:
2026-09-27-resolve-project-graph-paths-by-case-and-through-a-symlinked-config)."""

from pathlib import Path

import pytest

from test_worktree_sibling_nodes import config, git, repo, validate, workspace  # noqa: F401


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


def test_a_symlinked_config_belongs_to_the_folder_it_sits_in(tmp_path):
    node = repo(tmp_path / "node")
    store = tmp_path / "store"
    config(store, "nd", children={"kid": "kid"})
    (node / "tcw-config.yaml").symlink_to(store / "tcw-config.yaml")
    config(node / "kid", "kid", parent={"nd": ".."})
    done = validate(node)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "not reachable" not in done.stdout + done.stderr


def submodule_workspace(workspace: Path, tmp_path: Path) -> Path:  # noqa: F811
    lib = repo(tmp_path / "lib-origin")
    config(lib, "lib", parent={"app-repo": ".."})
    git(lib, "add", "-A")
    git(lib, "commit", "-qm", "lib")
    app = workspace / "app"
    git(app, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(lib), "lib")
    app_cfg = app / "tcw-config.yaml"
    app_cfg.write_text(app_cfg.read_text() + "    lib: lib\n")
    git(app, "add", "-A")
    git(app, "commit", "-qm", "lib submodule")
    ws_cfg = workspace / "tcw-config.yaml"
    ws_cfg.write_text(ws_cfg.read_text() + "    lib-too: app/lib\n")
    git(app, "worktree", "add", "-q", "../app-wt", "-b", "feature")
    git(workspace / "app-wt", "-c", "protocol.file.allow=always", "submodule", "update",
        "--init", "-q")
    return workspace / "app-wt"


def test_a_submodule_node_inside_a_linked_worktree_loads_once(workspace, tmp_path):  # noqa: F811
    wt = submodule_workspace(workspace, tmp_path)
    done = validate(wt / "lib")
    assert "duplicate project id" not in done.stdout + done.stderr, done.stdout + done.stderr


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
