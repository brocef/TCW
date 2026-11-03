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



def test_nested_worktrees_lacking_a_sibling_do_not_find_the_real_one(tmp_path):
    """The copy's outer checkout is itself a linked worktree, so the main
    checkout's neighbours are never searched: they are the original's."""
    ws = _repository(tmp_path / "real" / "ws")
    r1, r2 = _siblings(ws)
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(r1, copy / "r1")
    found = tcw(copy / "r1", "project", "path", "r2")
    assert found.code != 0, found
    assert str(r2) not in found.out + found.err

def test_a_3x_copy_where_a_worktrees_path_lands_is_reported_not_the_mains(tmp_path):
    """The evaluation of candidate 6: two repositories side by side, `p`
    placing `e` with `../e`, each with a linked worktree side by side in
    another folder. The worktree of `e` is still 3.x while the main checkout
    of `e` is 4.0. From the worktree of `p`, the path lands on the 3.x copy
    in the worktree, which is the project to migrate; the main checkout's
    copy, on another branch, is never read in its place."""
    main_p = proj(tmp_path / "m" / "p", "p")
    main_e = proj(tmp_path / "m" / "e", "e")
    write_manifest(main_p, {"e": "../e"})
    for repo in (main_p, main_e):
        git(repo, "init", "-q", "-b", "main")
        _commit_all(repo)
    k_p = _linked(main_p, tmp_path / "k" / "p")
    k_e = _linked(main_e, tmp_path / "k" / "e")
    (k_e / ".tcw" / "tcw-config.yaml").unlink()
    (k_e / "tcw-config.yaml").write_text("id: e\n")
    found = tcw(k_p, "project", "path", "e")
    assert found.code != 0, found
    assert str(k_e) in found.err and "tcw migrate" in found.err, found.err
    assert str(main_e.resolve()) not in found.out + found.err
    # Once the worktree's copy is migrated too, it is the one read.
    (k_e / "tcw-config.yaml").unlink()
    proj(k_e, "e")
    found = tcw(k_p, "project", "path", "e")
    assert (found.code, found.out.strip()) == (0, str(k_e)), found


def test_a_3x_copy_in_the_worktree_stands_for_the_mains_path(tmp_path):
    """The same, inside one repository: `r` holds `a` and `b`, and `a`'s
    personal manifest places `b` by its path in the main checkout. In the
    linked worktree `b` is still 3.x while the main checkout's `b` is 4.0:
    the worktree's 3.x copy is the one reported, never the main checkout's."""
    main = tmp_path / "m" / "r"
    proj(main / "a", "a")
    main_b = proj(main / "b", "b")
    git(main, "init", "-q", "-b", "main")
    _commit_all(main)
    worktree = _linked(main, tmp_path / "k" / "r")
    write_manifest(worktree / "a", {"b": str(main_b)}, local=True)
    (worktree / "b" / ".tcw" / "tcw-config.yaml").unlink()
    (worktree / "b" / "tcw-config.yaml").write_text("id: b\n")
    found = tcw(worktree / "a", "project", "path", "b", env=personal_env(tmp_path))
    assert found.code != 0, found
    assert str(worktree / "b") in found.err and "tcw migrate" in found.err, found.err
    assert str(main_b.resolve()) not in found.out + found.err


def test_a_worktree_finds_a_sibling_repositorys_project_in_the_worktree_set(tmp_path):
    """The evaluation of candidate 7: a top project `top` and two code
    repositories `a` and `b` side by side, `top`'s manifest placing both, and
    each with a linked worktree side by side in another folder, all on 4.0.
    From the worktree of `a`, the search finds `b` beside the main checkout,
    while `top`'s manifest, read as written, places it in the worktree of the
    same repository. That is one project in two checkouts, not a
    disagreement: the manifest's checkout is the one read."""
    main_top = proj(tmp_path / "m" / "top", "top")
    main_a = proj(tmp_path / "m" / "a", "a", parent=["top"])
    main_b = proj(tmp_path / "m" / "b", "b")
    write_manifest(main_top, {"a": "../a", "b": "../b"})
    write_manifest(main_a, {"top": "../top"})
    for repo in (main_top, main_a, main_b):
        git(repo, "init", "-q", "-b", "main")
        _commit_all(repo)
    _linked(main_top, tmp_path / "k" / "top")
    k_a = _linked(main_a, tmp_path / "k" / "a")
    k_b = _linked(main_b, tmp_path / "k" / "b")
    found = tcw(k_a, "project", "path", "b")
    assert (found.code, found.out.strip()) == (0, str(k_b)), found
    assert str(main_b.resolve()) not in found.out + found.err


def test_a_worktree_still_reports_a_sibling_found_in_another_repository(tmp_path):
    """The same shape, but the search finds `b` in a folder that is not a
    checkout of the repository the manifest's folder is in: that is still
    a disagreement, and still reported."""
    main_top = proj(tmp_path / "m" / "top", "top")
    main_a = proj(tmp_path / "m" / "a", "a", parent=["top"])
    proj(tmp_path / "m" / "b", "b")
    write_manifest(main_top, {"a": "../a", "b": "../b"})
    write_manifest(main_a, {"top": "../top"})
    for repo in (main_top, main_a):
        git(repo, "init", "-q", "-b", "main")
        _commit_all(repo)
    _linked(main_top, tmp_path / "k" / "top")
    k_a = _linked(main_a, tmp_path / "k" / "a")
    proj(tmp_path / "k" / "b", "b")
    found = tcw(k_a, "project", "path", "b")
    assert found.code != 0 and "is found at" in found.err, found


def _worktree_set(base: Path, parents: list[str]) -> tuple[Path, Path, Path]:
    """`top` placing `a` and `b`, `a` naming `parents` and placing `top`, each
    a repository in `base/m` with a linked worktree in `base/k`, all on 4.0:
    the worktree of `a`, and `b`'s main checkout and worktree."""
    main_top = proj(base / "m" / "top", "top")
    main_a = proj(base / "m" / "a", "a", parent=parents)
    main_b = proj(base / "m" / "b", "b")
    write_manifest(main_top, {"a": "../a", "b": "../b"})
    write_manifest(main_a, {"top": "../top"})
    for repo in (main_top, main_a, main_b):
        git(repo, "init", "-q", "-b", "main")
        _commit_all(repo)
    _linked(main_top, base / "k" / "top")
    return _linked(main_a, base / "k" / "a"), main_b, _linked(main_b, base / "k" / "b")


def test_a_sibling_the_search_finds_first_is_still_reported_from_a_worktree(tmp_path):
    """The same set, with `a` naming `b` before `top`: `b` is found by the
    search beside the main checkout before `top`'s manifest is read, and
    the folder in use is the search's. That is still reported, never the
    main checkout's copy read with no error (review of the fix)."""
    k_a, main_b, _ = _worktree_set(tmp_path, ["b", "top"])
    found = tcw(k_a, "project", "path", "b")
    assert found.code != 0 and "is found at" in found.err, found
    checked = tcw(k_a, "validate")
    assert checked.code != 0 and "is found at" in checked.out + checked.err, checked


def test_a_separate_clone_beside_the_worktree_still_disagrees(tmp_path):
    """The same set, with a separate clone of `b` in place of its linked
    worktree: two clones are two repositories, and still reported."""
    k_a, main_b, k_b = _worktree_set(tmp_path, ["top"])
    git(main_b, "worktree", "remove", "--force", str(k_b))
    subprocess.run(["git", "clone", "-q", str(main_b), str(k_b)], check=True,
                   capture_output=True, stdin=subprocess.DEVNULL)
    found = tcw(k_a, "project", "path", "b")
    assert found.code != 0 and "is found at" in found.err, found


# -- A copy kept inside the main checkout it was made from ------------------------------
#
# Claude Code keeps its worktrees at `.claude/worktrees/<name>`, inside the main
# checkout. Looking from where a worktree is, the search does not climb into
# the main checkout of a linked worktree kept inside it, nor into the folders
# between them that belong to that main checkout's repository: they are the
# copy's original, on another branch (TCW-120).

EMPTY_MANIFEST = "tcw-version: 4.0.0\nprojects: {}\n"


def _main_with_a_child(base: Path, *, root_3x: bool = False,
                       child_3x: str | None = None) -> tuple[Path, Path]:
    """Repository X at `base/MAIN` (project `r`, a manifest placing `p` at
    `p`) holding repository Y at `MAIN/p` (project `p`, naming nothing),
    each committed on `main`. `root_3x` makes X's `main` branch 3.x (a root
    `tcw-config.yaml`, no `.tcw/`); `child_3x` is Y's root `tcw-config.yaml`,
    written in place of its 4.0 files."""
    main = base / "MAIN"
    main.mkdir(parents=True)
    if root_3x:
        (main / "tcw-config.yaml").write_text("id: r\n")
    else:
        proj(main, "r")
        write_manifest(main, {"p": "p"})
    (main / ".gitignore").write_text("/p/\n/.claude/\n/.worktrees/\n")
    child = main / "p"
    child.mkdir()
    if child_3x is not None:
        (child / "tcw-config.yaml").write_text(child_3x)
    else:
        proj(child, "p")
        write_manifest(child, EMPTY_MANIFEST)
    for repo in (main, child):
        git(repo, "init", "-q", "-b", "main")
        _commit_all(repo)
    return main.resolve(), child.resolve()


def _copy(main: Path, child_main: Path, at: Path, *, child_at: str = "p"
          ) -> tuple[Path, Path]:
    """X's linked worktree at `at` and Y's at `at / child_at`."""
    w = _linked(main, at)
    return w, _linked(child_main, w / child_at)


def _migrate_branch(w: Path) -> None:
    """X's linked worktree `w` moved to 4.0 on its own branch."""
    (w / "tcw-config.yaml").unlink()
    proj(w, "r")
    write_manifest(w, {"p": "p"})
    _commit_all(w)


def _prints(cwd: Path, expected: Path, *argv: str) -> None:
    """`tcw <argv>` from `cwd` prints `expected` alone and exits 0."""
    ran = tcw(cwd, *argv)
    assert ran.code == 0, ran
    assert ran.out == f"{expected}\n", ran


def test_a_copy_kept_inside_its_own_main_checkout_finds_the_root_in_the_copy(tmp_path):
    """Spec case 1, AC 1: the copy's `r`, not "declared by more than one
    folder" naming the copy and MAIN."""
    main, child = _main_with_a_child(tmp_path)
    w, wp = _copy(main, child, main / ".claude" / "worktrees" / "w")
    ran = tcw(wp, "project", "path", "r")
    assert (ran.code, ran.out, ran.err) == (0, f"{w}\n", ""), ran


def test_a_copy_kept_inside_a_3x_main_checkout_finds_the_root_in_the_copy(tmp_path):
    """Spec case 2, AC 2: MAIN's branch is 3.x, the copy's is 4.0; MAIN is
    not read, so it is not reported as needing `tcw migrate`."""
    main, child = _main_with_a_child(tmp_path, root_3x=True)
    w, wp = _copy(main, child, main / ".claude" / "worktrees" / "w")
    _migrate_branch(w)
    ran = tcw(wp, "project", "path", "r")
    assert ran.code == 0 and ran.out == f"{w}\n", ran
    assert "tcw migrate" not in ran.err, ran


def test_a_copy_kept_outside_its_main_checkout_finds_the_root_in_the_copy(tmp_path):
    """Spec case 3, AC 3 (a control: it passes today)."""
    main, child = _main_with_a_child(tmp_path)
    w, wp = _copy(main, child, tmp_path / "elsewhere" / "w")
    _prints(wp, w, "project", "path", "r")


def test_a_worktree_in_a_linked_worktree_inside_its_main_checkout_finds_the_root_there(
        tmp_path):
    """Spec case 4, AC 4: Y's main checkout is beside MAIN, so the worktree
    is no copy, yet its first round's climb no longer reaches MAIN."""
    main, _ = _main_with_a_child(tmp_path)
    ymain = proj(tmp_path / "ymain", "p")
    write_manifest(ymain, EMPTY_MANIFEST)
    git(ymain, "init", "-q", "-b", "main")
    _commit_all(ymain)
    w = _linked(main, main / ".claude" / "worktrees" / "w")
    wp = _linked(ymain, w / ".worktrees" / "p")
    _prints(wp, w, "project", "path", "r")


def _repo(folder: Path, project_id: str, ignore: str, **relations) -> Path:
    """`folder` made a repository holding project `project_id`, ignoring
    `ignore`, committed on `main`."""
    root = proj(folder, project_id, **relations)
    (root / ".gitignore").write_text(ignore)
    git(root, "init", "-q", "-b", "main")
    _commit_all(root)
    return root


def test_a_copy_three_deep_finds_the_outermost_root_in_the_copy(tmp_path):
    """Spec case 5, AC 5: Z holds X holds Y; the copy is Z's linked worktree
    inside Z's main checkout, and the walk reaches it past X's worktree."""
    zm = _repo(tmp_path / "ZM", "z", "/x/\n/.claude/\n")
    xm = _repo(zm / "x", "x", "/y/\n")
    ym = _repo(xm / "y", "y", "")
    w = _linked(zm, zm / ".claude" / "worktrees" / "w")
    _linked(xm, w / "x")
    wy = _linked(ym, w / "x" / "y")
    _prints(wy, w, "project", "path", "z")


def test_a_clone_between_the_worktrees_does_not_hide_the_outer_one(tmp_path):
    """Spec case 7, AC 5a: a plain repository at `zw/x` lies between Y's
    worktree and Z's linked worktree `zw`; the walk does not stop at it."""
    zm = _repo(tmp_path / "ZM", "z", "/.claude/\n")
    zw = _linked(zm, zm / ".claude" / "worktrees" / "zw")
    _repo(zw / "x", "x", "/.worktrees/\n")
    ym = _repo(tmp_path / "ymain", "y", "")
    wy = _linked(ym, zw / "x" / ".worktrees" / "y")
    _prints(wy, zw, "project", "path", "z")


def test_a_related_projects_search_inside_the_copy_finds_the_root_in_the_copy(tmp_path):
    """Spec case 8, AC 5b: X is a monorepo whose child `s` names `r`; the
    search for `r` is made from the copy's `s`, outside the active
    project's worktree, and it too keeps out of MAIN."""
    main = proj(tmp_path / "MAIN", "r")
    write_manifest(main, {"p": "p"})
    proj(main / "s", "s", parent=["r"])
    (main / ".gitignore").write_text("/p/\n/.claude/\n")
    git(main, "init", "-q", "-b", "main")
    _commit_all(main)
    child = proj(main / "p", "p", parent=["s"])
    write_manifest(child, {"s": "../s"})
    git(child, "init", "-q", "-b", "main")
    _commit_all(child)
    w, wp = _copy(main, child, main / ".claude" / "worktrees" / "w")
    _prints(wp, w, "project", "path", "r")
    listed_ = tcw(wp, "project", "list")
    assert listed_.code == 0, listed_


def test_a_clone_kept_in_a_copy_inside_its_main_checkout_finds_the_root_in_the_copy(
        tmp_path):
    """Spec case 9, AC 5c: the active project is a plain repository, with
    no worktree of its own, kept in WS's linked worktree inside WS."""
    ws = _repo(tmp_path / "WS", "ws", "/x/\n/.claude/\n")
    w = _linked(ws, ws / ".claude" / "worktrees" / "w")
    x = _repo(w / "x", "x", "")
    _prints(x, w, "project", "path", "ws")


def test_a_separate_repository_between_the_copy_and_its_main_checkout_is_still_searched(
        tmp_path):
    """Spec case 10, AC 5d: `MAIN/tools` is a repository of its own, and the
    copy is kept inside it. It lies between the copy and MAIN but is not
    MAIN's repository, so it is still searched; MAIN is not."""
    main = _repo(tmp_path / "MAIN", "r", "/p/\n/tools/\n")
    tools = _repo(main / "tools", "tools", "/wt/\n")
    child = _repo(main / "p", "p", "")
    w, wp = _copy(main, child, tools / "wt" / "w")
    _prints(wp, tools, "project", "path", "tools")
    _prints(wp, w, "project", "path", "r")


def test_a_project_above_the_main_checkout_is_still_found_from_the_copy(tmp_path):
    """AC 5e: the folders above MAIN stay in the climb, so a project at the
    folder holding MAIN, declared nowhere else, is found from the copy."""
    above = proj(tmp_path, "o")
    main, child = _main_with_a_child(tmp_path)
    _, wp = _copy(main, child, main / ".claude" / "worktrees" / "w")
    _prints(wp, above, "project", "path", "o")


def test_a_copy_inside_its_main_checkout_lacking_the_root_does_not_find_the_mains(
        tmp_path):
    """Spec case 6, AC 6: with `r` removed from the copy's working folder,
    MAIN's `r` is not read in its place: the answer is "not found", as
    `test_nested_worktrees_lacking_a_sibling_do_not_find_the_real_one`
    has it for a copy kept elsewhere."""
    main, child = _main_with_a_child(tmp_path)
    w, wp = _copy(main, child, main / ".claude" / "worktrees" / "w")
    (w / ".tcw" / "tcw-config.yaml").unlink()
    ran = tcw(wp, "project", "path", "r")
    assert ran.code != 0 and ran.out == "", ran
    assert str(main) not in (ran.out + ran.err).replace(str(w), ""), ran
    assert "no project with ID 'r' is known or found" in ran.err, ran


def test_a_worktree_in_a_main_checkouts_worktrees_folder_finds_that_checkouts_project(
        tmp_path):
    """AC 9 (a control): Y's worktree kept in X's *main* checkout, with no
    linked worktree of X around it, still finds MAIN's `r`."""
    main, child = _main_with_a_child(tmp_path)
    wp = _linked(child, main / ".worktrees" / "p")
    _prints(wp, main, "project", "path", "r")


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
