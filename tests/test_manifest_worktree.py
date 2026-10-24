"""Manifests and the lookup in a linked git worktree (TCW-107 Design 4,
acceptance criteria 16-19 and 26).

Every test builds a real git repository and a linked worktree with
`git worktree add`, never a simulated one: the rules turn on what git reports
about the folder, and on the main checkout being somewhere else on disk.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from tests.projectfiles import write_config, write_local_config, write_manifest
from tests.test_project_files_cli import personal_env, tcw


def proj(root: Path, project_id: str, **relations) -> Path:
    """A project at `root` declaring `project_id`, naming other projects by
    ID only: `parent=[...]` as parents passing every axis, `upstream=[...]` as
    parents passing none, after them, and `children=[...]` as children."""
    data: dict = {"id": project_id}
    parents = list(relations.get("parent", ())) + [
        {"id": i, "inherit": "none"} for i in relations.get("upstream", ())]
    if parents:
        data["parents"] = parents
    if relations.get("children"):
        data["children"] = list(relations["children"])
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def git(root: Path, *argv: str) -> str:
    return subprocess.run(["git", "-C", str(root), *argv], check=True,
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout


def repository_with_worktree(main: Path, worktree: Path) -> Path:
    """`main` made a git repository holding what is in it, with a linked
    worktree at `worktree` on a new branch."""
    (main / "docs" / "work").mkdir(parents=True, exist_ok=True)
    (main / "docs" / "work" / ".gitkeep").write_text("")
    git(main, "init", "-q")
    git(main, "add", "-A")
    git(main, "commit", "-qm", "fixture")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    git(main, "worktree", "add", "-q", "-b", "feature", str(worktree))
    return worktree.resolve()


def listed(cwd: Path, env: dict | None = None) -> dict:
    ran = tcw(cwd, "project", "list", "--json", env=env)
    assert ran.code == 0, ran
    return {row["id"]: row for row in json.loads(ran.out)["projects"]}


def test_ac16_tracked_files_come_from_the_worktree(tmp_path):
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    proj(tmp_path / "lib", "lib")
    lib2 = proj(tmp_path / "lib2", "lib")
    write_manifest(app, {"lib": "../lib"})
    worktree = repository_with_worktree(app, tmp_path / "elsewhere" / "wt")
    write_manifest(worktree, {"lib": "../lib2"})
    assert listed(worktree)["lib"]["path"] == str(lib2)


def test_ac17_personal_files_fall_back_to_the_main_checkouts(tmp_path):
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    proj(tmp_path / "lib", "lib")
    held = proj(tmp_path / "held" / "lib", "lib")
    mine = proj(tmp_path / "mine" / "lib", "lib")
    write_manifest(app, {"lib": "../lib"})
    worktree = repository_with_worktree(app, tmp_path / "elsewhere" / "wt")
    env = personal_env(tmp_path)
    main_manifest = write_manifest(app, {"lib": str(held)}, local=True)
    row = listed(worktree, env)["lib"]
    assert (row["path"], row["found"]["file"]) == (str(held), str(main_manifest))
    own = write_manifest(worktree, {"lib": str(mine)}, local=True)
    row = listed(worktree, env)["lib"]
    assert (row["path"], row["found"]["file"]) == (str(mine), str(own.resolve()))


def test_ac17_the_main_checkouts_personal_configuration(tmp_path):
    app = proj(tmp_path / "app", "app")
    worktree = repository_with_worktree(app, tmp_path / "elsewhere" / "wt")
    local = write_local_config(app, (
        "user:\n  name: Someone Else\nwork:\n  stages:\n    spec:\n      prompt:\n"
        "        - file: docs/x.md\n"
        "        - generate: 'printf \"config-dir=%s\\n\" \"$TCW_CONFIG_DIR\"'\n"))
    (app / "docs" / "x.md").write_text("WORDS FROM THE MAIN CHECKOUT\n")
    (worktree / "docs" / "x.md").write_text("WORDS FROM THE WORKTREE\n")
    env = personal_env(tmp_path)
    shown = tcw(worktree, "project", "config", "--origin", env=env)
    assert shown.code == 0, shown
    assert f"name: Someone Else  # local: {local}" in shown.out, shown.out
    prompt = tcw(worktree, "work", "stage", "prompt", "spec", env=env)
    assert prompt.code == 0, prompt
    assert "WORDS FROM THE WORKTREE" in prompt.out
    assert "WORDS FROM THE MAIN CHECKOUT" not in prompt.out
    assert f"config-dir={worktree}\n" in prompt.out, prompt.out


def test_ac18_outside_the_repository_from_the_main_checkout(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["app"])
    app = proj(tmp_path / "ws" / "app", "app", parent=["ws"], upstream=["lib"])
    lib = proj(tmp_path / "ws" / "lib", "lib")
    write_manifest(ws, {"app": "app"})
    worktree = repository_with_worktree(app, tmp_path / "elsewhere" / "wt")
    rows = listed(worktree)
    assert (rows["lib"]["path"], rows["lib"]["found"]) == (str(lib), {"by": "search"})
    assert (rows["ws"]["path"], rows["ws"]["found"]) == (str(ws), {"by": "search"})
    ran = tcw(worktree, "validate")
    assert ran.code == 0, ran
    assert "duplicate project id" not in ran.out


def test_a_project_below_the_worktrees_top_finds_what_encloses_the_main_checkout(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["a"])
    repo = tmp_path / "ws" / "repo"
    proj(repo / "packages" / "a", "a", parent=["ws"])
    write_manifest(ws, {"a": "repo/packages/a"})
    worktree = repository_with_worktree(repo, tmp_path / "elsewhere" / "wt")
    rows = listed(worktree / "packages" / "a")
    assert (rows["ws"]["path"], rows["ws"]["found"]) == (str(ws), {"by": "search"})


def test_ac19_one_project_not_two(tmp_path):
    lib = proj(tmp_path / "lib", "lib", children=["app"])
    app = proj(tmp_path / "app", "app", parent=["lib"])
    write_manifest(lib, {"app": "../app"})
    worktree = repository_with_worktree(app, tmp_path / "elsewhere" / "wt")
    ran = tcw(worktree, "validate")
    assert ran.code == 0, ran
    assert "duplicate project id" not in ran.out
    assert "nonreciprocal" not in ran.out
    rows = listed(worktree)
    assert (rows["app"]["relation"], rows["app"]["path"]) == ("current", str(worktree))
    assert rows["lib"]["path"] == str(lib)


def test_ac19_a_search_landing_in_the_main_checkout_is_the_worktrees_copy(tmp_path):
    """Design 4.4 for the search: `lib`, with no manifest, finds its child
    `app` next to it, which is the main checkout; the worktree's copy is the
    same project."""
    lib = proj(tmp_path / "lib", "lib", children=["app"])
    proj(tmp_path / "app", "app", parent=["lib"])
    worktree = repository_with_worktree(tmp_path / "app", tmp_path / "elsewhere" / "wt")
    ran = tcw(worktree, "validate")
    assert ran.code == 0, ran
    assert "duplicate project id" not in ran.out
    assert listed(worktree)["lib"]["path"] == str(lib)


def test_ac26_a_worktree_inside_the_main_checkout(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["app"])
    app = proj(tmp_path / "ws" / "app", "app", parent=["ws"])
    write_manifest(ws, {"app": "app"})
    worktree = repository_with_worktree(app, app / ".worktrees" / "feature")
    ran = tcw(worktree, "validate")
    assert ran.code == 0, ran
    assert "duplicate project id" not in ran.out
    assert listed(worktree)["ws"]["path"] == str(ws)


def test_a_borrowed_personal_manifest_reports_a_missing_project_once(tmp_path):
    """A worktree with no personal manifest of its own reads the main
    checkout's (Design 4.2). When that file places a project in a folder that
    is not here, `tcw validate` in the worktree reports it once, as it does in
    the main checkout, not once for the lookup and again for the entry."""
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    (app / ".gitignore").write_text("/.tcw/tcw-manifest.local.yaml\n")
    write_manifest(app, {"lib": "../gone"}, local=True)
    worktree = repository_with_worktree(app, tmp_path / "wt")
    env = personal_env(tmp_path)
    for cwd in (app, worktree):
        ran = tcw(cwd, "validate", env=env)
        assert ran.code == 0, (cwd, ran)
        assert ran.out.count("unresolved: ") == 1, (cwd, ran)
        assert "0 errors, 0 warnings, 1 unresolved" in ran.err, (cwd, ran)
