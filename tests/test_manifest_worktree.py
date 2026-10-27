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
    assert f"name: Someone Else  # app, local {local}" in shown.out, shown.out
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


# -- A copy made of linked worktrees, one inside another --------------------------------
#
# A relative path is first read as written: when it lands on a project in a
# checkout of the repository its entry names (any repository, when none is
# named), other than one of this project's own repository, it is read there.
# Only otherwise is it read beside the main checkout.

WS_URL = "https://example.invalid/ws.git"


def _workspace(base: Path, url: str = WS_URL) -> Path:
    """A workspace repository (with `url` as its remote) holding its child's
    work store, and the child, a repository of its own, inside its folder."""
    ws = proj(base / "ws", "ws", children=["app"])
    (ws / ".gitignore").write_text("/*\n!/.gitignore\n!/.tcw/\n!/docs/\n")
    (ws / "docs" / "app" / "work").mkdir(parents=True)
    (ws / "docs" / "app" / "work" / ".gitkeep").write_text("")
    write_manifest(ws, {"app": "app"})
    app = ws / "app"
    write_config(app, "id: app\nparents:\n- ws\nwork:\n  path: tcw://ws.path/docs/app/work\n")
    write_manifest(app, {"ws": {"path": "..", "repository": f"{url}#main"}})
    git(ws, "init", "-q", "-b", "main")
    git(ws, "remote", "add", "origin", WS_URL)
    git(app, "init", "-q", "-b", "main")
    for repo in (ws, app):
        git(repo, "add", "-A")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")
    return ws.resolve()


def _linked(main: Path, at: Path) -> Path:
    at.parent.mkdir(parents=True, exist_ok=True)
    git(main, "worktree", "add", "-q", "--detach", str(at))
    return at.resolve()


def _where(cwd: Path) -> tuple[str, str]:
    """`tcw project path ws` and the work store `tcw project info` names."""
    path = tcw(cwd, "project", "path", "ws")
    info = tcw(cwd, "project", "info")
    assert path.code == 0 and info.code == 0, (path, info)
    store = next(line for line in info.out.splitlines() if line.strip().startswith("work:"))
    return path.out.strip(), store.split(":", 1)[1].strip()


def test_nested_worktrees_read_the_workspace_in_the_copy(tmp_path):
    ws = _workspace(tmp_path / "real")
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(ws / "app", copy / "app")
    assert _where(copy / "app") == (str(copy), str(copy / "docs" / "app" / "work"))


def test_nested_worktrees_whose_entry_names_another_repository_read_beside_the_main(tmp_path):
    ws = _workspace(tmp_path / "real", url="https://example.invalid/other.git")
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(ws / "app", copy / "app")
    assert _where(copy / "app")[0] == str(ws)


def test_a_worktree_made_away_from_the_workspace_reads_beside_the_main(tmp_path):
    ws = _workspace(tmp_path / "real")
    linked = _linked(ws / "app", tmp_path / "elsewhere" / "app")
    assert _where(linked) == (str(ws), str(ws / "docs" / "app" / "work"))


def test_clones_nested_alike_read_the_clone(tmp_path):
    ws = _workspace(tmp_path / "real")
    clone = tmp_path / "clone" / "ws"
    subprocess.run(["git", "clone", "-q", str(ws), str(clone)], check=True)
    subprocess.run(["git", "clone", "-q", str(ws / "app"), str(clone / "app")], check=True)
    clone = clone.resolve()
    assert _where(clone / "app") == (str(clone), str(clone / "docs" / "app" / "work"))


def test_nested_worktrees_search_the_copy_for_an_enclosing_project(tmp_path):
    """The search for a project with no manifest entry follows the same rule:
    the worktree's folder lies inside another repository's checkout, so the
    folders enclosing it are the copy's own."""
    ws = _workspace(tmp_path / "real")
    write_manifest(ws / "app", "tcw-version: 4.0.0\nprojects: {}\n")
    git(ws / "app", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "no entry")
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(ws / "app", copy / "app")
    assert _where(copy / "app") == (str(copy), str(copy / "docs" / "app" / "work"))
    linked = _linked(ws / "app", tmp_path / "elsewhere" / "app")
    assert _where(linked)[0] == str(ws)


# -- The search from a worktree inside another repository's checkout --------------------
#
# The worktree's own neighbours are searched first, then the main checkout's,
# as before: a folder holding the worktree can lie in another repository's
# checkout without the worktree being a copy, as a workspace repository's
# `.worktrees/` folder or a home folder kept in git does.


def _commit_all(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")


def _siblings(holder: Path) -> tuple[Path, Path]:
    """Two repositories side by side in `holder`: `r1`, whose project has a
    parent `r2` that no manifest entry places, and `r2`."""
    r1 = proj(holder / "r1", "r1", parent=["r2"])
    r2 = proj(holder / "r2", "r2")
    for repo in (r1, r2):
        write_manifest(repo, "tcw-version: 4.0.0\nprojects: {}\n")
        git(repo, "init", "-q", "-b", "main")
        _commit_all(repo)
    return r1, r2


def _repository(folder: Path) -> Path:
    """`folder` made a git repository of its own, ignoring what is in it."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".gitignore").write_text("/*\n!/.gitignore\n")
    git(folder, "init", "-q", "-b", "main")
    _commit_all(folder)
    return folder.resolve()


def test_a_worktree_in_a_workspace_repositorys_worktrees_folder_finds_a_sibling(tmp_path):
    ws = _repository(tmp_path / "ws")
    r1, r2 = _siblings(ws)
    linked = _linked(r1, ws / ".worktrees" / "r1-feat")
    found = tcw(linked, "project", "path", "r2")
    assert found.code == 0, found
    assert found.out.strip() == str(r2)


def test_a_worktree_in_a_home_folder_kept_in_git_finds_a_sibling(tmp_path):
    home = _repository(tmp_path / "home")
    r1, r2 = _siblings(home / "code")
    linked = _linked(r1, home / "elsewhere" / "r1-feat")
    found = tcw(linked, "project", "path", "r2")
    assert found.code == 0, found
    assert found.out.strip() == str(r2)


def test_a_plain_worktree_elsewhere_finds_a_sibling_beside_the_main(tmp_path):
    r1, r2 = _siblings(tmp_path / "code")
    linked = _linked(r1, tmp_path / "elsewhere" / "r1-feat")
    found = tcw(linked, "project", "path", "r2")
    assert found.code == 0, found
    assert found.out.strip() == str(r2)


def test_nested_worktrees_find_the_copys_sibling_before_the_real_one(tmp_path):
    """Both are there: the worktree's own neighbours come first."""
    ws = _repository(tmp_path / "real" / "ws")
    r1, r2 = _siblings(ws)
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(r1, copy / "r1")
    copied = _linked(r2, copy / "r2")
    found = tcw(copy / "r1", "project", "path", "r2")
    assert found.code == 0, found
    assert found.out.strip() == str(copied)


# -- A store path whose store declares a repository -------------------------------------
#
# `<component>.path` sits beside `<component>.repository`, so a path read as
# written must land in a checkout of the declared repository, as `tcw migrate`
# reads it (tests/migrate/test_migrate_locations.py).


def _workspace_with_a_store_path(base: Path, url: str) -> Path:
    """`_workspace`, with the child's store named by a relative path and
    declared to be in the repository `url`."""
    ws = _workspace(base)
    write_config(ws / "app", "id: app\nparents:\n- ws\nwork:\n  path: ../docs/app/work\n"
                             f"  repository:\n    url: {url}\n    path: docs/app/work\n")
    _commit_all(ws / "app")
    return ws


def test_nested_worktrees_whose_store_names_another_repository_read_it_beside_the_main(
        tmp_path):
    ws = _workspace_with_a_store_path(tmp_path / "real", "https://example.invalid/other.git")
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(ws / "app", copy / "app")
    assert _where(copy / "app")[1] == str(ws / "docs" / "app" / "work")


def test_nested_worktrees_whose_store_names_the_copys_repository_read_it_in_the_copy(
        tmp_path):
    ws = _workspace_with_a_store_path(tmp_path / "real", WS_URL)
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(ws / "app", copy / "app")
    assert _where(copy / "app")[1] == str(copy / "docs" / "app" / "work")
