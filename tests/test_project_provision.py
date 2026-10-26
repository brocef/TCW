"""`tcw project provision` fetching projects (TCW-115 Design 7; AC 19 to 38).

Every remote is a bare repository in the test's own folder, and every run
goes through the stand-in `git` (`tests/provision_support.py`), which counts
the clones it lets through and refuses any other call that would contact a
remote. `HOME` is outside `<tmp>` unless a case sets its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from tests.projectfiles import (config_file, connect_projects, write_config,
                                write_manifest)
from tests.provision_support import (make_remote, project_files, real_git,
                                     stand_in_git)  # noqa: F401  (a fixture)
from tests.test_project_files_cli import tcw
from tests.work.projects import make_project

PERSONAL = {"TCW_NO_PERSONAL_CONFIG": None}


def provision(cwd, *argv, env=None):
    return tcw(cwd, "project", "provision", *argv, env=env)


def listing(cwd) -> dict:
    done = tcw(cwd, "project", "list", "--json")
    assert done.code == 0, done
    return {row["id"]: row for row in json.loads(done.out)["projects"]}


def staging_left(folder: Path) -> list[Path]:
    return sorted(folder.rglob(".tcw-staging-*"))


def tree_hash(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        digest.update(str(path.relative_to(folder)).encode())
        mode = os.lstat(path).st_mode
        digest.update(str(mode).encode())
        if path.is_file() and not path.is_symlink():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def app_project(tmp, *, parents=(), children=(), manifest=None, name="app"):
    app = make_project(tmp, name)
    if parents:
        connect_projects(app, "parent", *parents)
    if children:
        connect_projects(app, "children", *children)
    if manifest:
        write_manifest(app, manifest)
    return app


@pytest.fixture
def ac19(tmp_path, stand_in_git):
    """AC 19: `app` with parent `core`, which its manifest places at `../core`
    from a remote holding `core` at its top on `main`."""
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = app_project(tmp_path, parents=["core"],
                      manifest={"core": {"path": "../core", "repository": f"{remote}#main"}})
    stand_in_git.allow_clone()
    return app, remote


# -- AC 19: provision a parent ---------------------------------------------------------

def test_ac19_a_parent_is_fetched(tmp_path, ac19, stand_in_git):
    app, remote = ac19
    done = provision(app)
    assert done.code == 0, done
    core = (tmp_path / "core").resolve()
    assert f"→ core: {remote} at main → {core}" in done.err, done.err
    assert done.err.index("→ core:") < done.err.index(f"core: fetched into {core}"), done.err
    row = listing(app)["core"]
    assert row["present"] is True
    assert row["found"] == {"by": "manifest",
                            "file": str((app / ".tcw/tcw-manifest.yaml").resolve())}
    [clone] = stand_in_git.calls("clone")
    assert clone[0:6] == ["clone", "--quiet", "--branch", "main", "--", str(remote)], clone
    assert stand_in_git.calls("checkout") == []
    assert staging_left(tmp_path) == []
    assert real_git(core, "status", "--porcelain") == ""
    assert (core / ".tcw/tcw-config.yaml").read_text() == \
        project_files("core")[".tcw/tcw-config.yaml"]
    stand_in_git.reset()
    stand_in_git.allow_clone(False)
    again = provision(app)
    assert again.code == 0, again
    assert "nothing to fetch" in again.err, again.err
    assert stand_in_git.calls("clone") == []
    assert staging_left(tmp_path) == []


# -- AC 20 and AC 21: in turn, never a sibling, scoped to one project -------------------

@pytest.fixture
def ac20(tmp_path, stand_in_git):
    base = make_remote(tmp_path, "base", project_files("base"))
    other = make_remote(tmp_path, "other", project_files("other", parents=["core"]))
    core = make_remote(tmp_path, "core", project_files(
        "core", parents=["base"], children=["other"],
        manifest={"base": {"path": "../base", "repository": str(base)},
                  "other": {"path": "../other", "repository": str(other)}}))
    kk = make_remote(tmp_path, "kk", project_files("kk", parents=["k"]))
    k = make_remote(tmp_path, "k", project_files(
        "k", parents=["app"], children=["kk"],
        manifest={"kk": {"path": "../kk", "repository": str(kk)},
                  "app": {"path": "../app"}}))
    app = app_project(tmp_path, parents=["core"], children=["k"],
                      manifest={"core": {"path": "../core", "repository": str(core)},
                                "k": {"path": "../k", "repository": str(k)}})
    stand_in_git.allow_clone()
    return app, {"base": base, "other": other, "core": core, "k": k, "kk": kk}


def _cloned(stand_in_git) -> list[str]:
    return [Path(call[-2]).name.removesuffix(".git") for call in stand_in_git.calls("clone")]


def test_ac20_in_turn_and_never_a_sibling(tmp_path, ac20, stand_in_git):
    app, _ = ac20
    done = provision(app)
    assert done.code == 0, done
    cloned = _cloned(stand_in_git)
    assert sorted(cloned) == ["base", "core", "k", "kk"], cloned
    assert cloned.index("core") < cloned.index("base")
    assert cloned.index("k") < cloned.index("kk")
    assert not (tmp_path / "other").exists()


def test_ac21_scoped_to_one_project(tmp_path, ac20, stand_in_git):
    app, _ = ac20
    done = provision(app, "core")
    assert done.code == 0, done
    assert sorted(_cloned(stand_in_git)) == ["base", "core"], done.err
    stand_in_git.reset()
    done = provision(app, "k")
    assert done.code == 0, done
    assert _cloned(stand_in_git) == ["k"], done.err
    assert not (tmp_path / "kk").exists()


def test_ac21_the_active_project_fetches_its_ancestors_only(tmp_path, ac20, stand_in_git):
    app, _ = ac20
    done = provision(app, "app")
    assert done.code == 0, done
    assert f"app: already on this machine at {app.resolve()}" in done.err, done.err
    assert sorted(_cloned(stand_in_git)) == ["base", "core"], done.err


def test_ac21_a_named_project_leaves_the_stores_alone(tmp_path, ac20, stand_in_git):
    app, _ = ac20
    store = make_remote(tmp_path, "store", {"docs/taxonomy/.keep": ""})
    _declare_store(app, "taxonomy", str(store))
    assert provision(app, "core").code == 0
    assert "store" not in _cloned(stand_in_git)


def _declare_store(app, axis, url):
    import yaml
    from tests.projectfiles import write_config_file
    document = yaml.safe_load(config_file(app).read_text())
    document[axis] = {"repository": {"url": url}}
    write_config_file(config_file(app), yaml.safe_dump(document, sort_keys=False))


def test_ac21_component_fetches_the_store_and_no_project(tmp_path, ac20, stand_in_git):
    app, _ = ac20
    (app / "docs" / "work").rename(app / "docs" / "work-old")
    store = make_remote(tmp_path, "store", {"README.md": "a work store\n"})
    _declare_store(app, "work", str(store))
    done = provision(app, "--component", "work")
    assert _cloned(stand_in_git) == ["store"], done
    assert not (tmp_path / "core").exists()


def test_ac21_a_project_and_a_component_is_a_usage_error(ac19, stand_in_git):
    app, _ = ac19
    assert provision(app, "core", "--component", "work").code == 2
    assert provision(app, "Core").code == 2
    assert stand_in_git.calls("clone") == []


# -- AC 22: already here, by every rule ------------------------------------------------

def _assert_untouched(done, stand_in_git):
    assert done.code == 0, done
    assert stand_in_git.calls("clone") == []
    assert "would fetch" not in done.err and "core: fetched" not in done.err, done.err


@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_ac22_a_the_projects_own_entry_decides(tmp_path, stand_in_git, flags):
    make_project(tmp_path, "core")
    remote = make_remote(tmp_path, "core", project_files("core"))
    ws = make_project(tmp_path, "ws")
    write_manifest(ws, {"core": {"path": "../elsewhere/core", "repository": str(remote)}})
    app = app_project(tmp_path, parents=["core", "ws"],
                      manifest={"core": "../core", "ws": "../ws"})
    stand_in_git.allow_clone()
    _assert_untouched(provision(app, *flags), stand_in_git)


@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_ac22_b_the_variable_places_it(tmp_path, stand_in_git, flags):
    remote = make_remote(tmp_path, "core", project_files("core"))
    copy = make_project(tmp_path / "copies", "core")
    app = app_project(tmp_path, parents=["core"],
                      manifest={"core": {"path": "../core", "repository": str(remote)}})
    stand_in_git.allow_clone()
    done = provision(app, *flags, env={"TCW_PROJECT_CORE": str(copy)})
    _assert_untouched(done, stand_in_git)


@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_ac22_c_the_search_finds_it(tmp_path, stand_in_git, flags):
    make_project(tmp_path, "core")
    app = app_project(tmp_path, parents=["core"])
    _assert_untouched(provision(app, *flags), stand_in_git)


def test_ac22_a_variable_naming_nothing_leaves_the_entry_to_decide(tmp_path, stand_in_git):
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = app_project(tmp_path, parents=["core"],
                      manifest={"core": {"path": "../core", "repository": str(remote)}})
    stand_in_git.allow_clone()
    done = provision(app, env={"TCW_PROJECT_CORE": str(tmp_path / "nowhere")})
    assert done.code == 0, done
    assert (tmp_path / "core" / ".tcw").is_dir()
    assert not (tmp_path / "nowhere").exists()


def test_ac22_a_project_already_here_is_read_for_its_links(tmp_path, stand_in_git):
    base = make_remote(tmp_path, "base", project_files("base"))
    core = make_project(tmp_path, "core")
    connect_projects(core, "parent", "base")
    write_manifest(core, {"base": {"path": "../base", "repository": str(base)}})
    app = app_project(tmp_path, parents=["core"], manifest={"core": "../core"})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 0, done
    assert _cloned(stand_in_git) == ["base"]


# -- AC 23: one clone for one repository folder ----------------------------------------

def _mono(tmp_path, *, client=True, top=None):
    files = project_files("server", at="apps/server")
    if client:
        files.update(project_files("client", at="apps/client"))
    if top is not None:
        files.update(project_files(top))
    return make_remote(tmp_path, "mono", files)


def _mono_app(tmp_path, remote, client_remote=None):
    entry = lambda sub, url: {"path": f"../mono/{sub}", "repository": str(url),  # noqa: E731
                              "subfolder": sub}
    return app_project(tmp_path, parents=["server", "client"], manifest={
        "server": entry("apps/server", remote),
        "client": entry("apps/client", client_remote or remote)})


def test_ac23_one_clone_serves_both(tmp_path, stand_in_git):
    app = _mono_app(tmp_path, _mono(tmp_path))
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 0, done
    assert len(stand_in_git.calls("clone")) == 1
    rows = listing(app)
    assert rows["server"]["present"] and rows["client"]["present"], rows


def test_ac23_two_repositories_at_one_folder_are_both_refused(tmp_path, stand_in_git):
    other = make_remote(tmp_path, "other", project_files("client", at="apps/client"))
    app = _mono_app(tmp_path, _mono(tmp_path), client_remote=other)
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert stand_in_git.calls("clone") == []
    folder = str((tmp_path / "mono").resolve())
    assert done.err.count(f"{folder} is placed by entries naming different") == 2, done.err


def test_ac23_a_clone_without_the_other_project(tmp_path, stand_in_git):
    app = _mono_app(tmp_path, _mono(tmp_path, client=False))
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "has no TCW project at apps/client" in done.err, done.err
    assert listing(app)["server"]["present"] is True


# -- AC 24: occupied, empty and `.git`-only folders -------------------------------------

def test_ac24_an_occupied_folder(tmp_path, ac19, stand_in_git):
    app, _ = ac19
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "f").write_text("mine\n")
    done = provision(app)
    assert done.code == 1, done
    assert stand_in_git.calls("clone") == []
    assert (tmp_path / "core" / "f").read_text() == "mine\n"
    assert f"{(tmp_path / 'core').resolve()} is not empty" in done.err, done.err
    assert str(app / ".tcw/tcw-manifest.yaml") in done.err, done.err


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a folder whatever its mode")
def test_ac24_an_unreadable_folder(tmp_path, ac19, stand_in_git):
    """A target folder that cannot be listed is refused, naming it, with no
    traceback, and nothing is written or removed (review round 1, finding 3)."""
    app, _ = ac19
    core = tmp_path / "core"
    core.mkdir()
    (core / "f").write_text("mine\n")
    listing_before = sorted(p.name for p in tmp_path.iterdir())
    core.chmod(0)
    try:
        done = provision(app)
    finally:
        core.chmod(0o755)
    assert done.code == 1, done
    assert "Traceback" not in done.err, done.err
    assert f"{core.resolve()} cannot be listed" in done.err, done.err
    assert stand_in_git.calls("clone") == []
    assert (core / "f").read_text() == "mine\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == listing_before
    assert staging_left(tmp_path) == []


def test_ac24_an_empty_folder_is_filled(tmp_path, ac19):
    app, _ = ac19
    (tmp_path / "core").mkdir()
    assert provision(app).code == 0
    assert (tmp_path / "core" / ".tcw" / "tcw-config.yaml").is_file()


@pytest.mark.parametrize("shape", ["file", "folder", "beside"])
def test_ac24_a_folder_holding_only_git(tmp_path, ac19, stand_in_git, shape):
    app, _ = ac19
    core = tmp_path / "core"
    core.mkdir()
    if shape == "file":
        (core / ".git").write_text("gitdir: ../.git/modules/core\n")
    else:
        (core / ".git").mkdir()
        (core / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    if shape == "beside":
        (core / ".DS_Store").write_text("")
    before, listing_before = tree_hash(core), sorted(p.name for p in tmp_path.iterdir())
    done = provision(app)
    assert done.code == 1, done
    assert stand_in_git.calls("clone") == []
    if shape == "beside":
        assert "is not empty" in done.err, done.err
    else:
        assert "holds only .git" in done.err and "finish or remove it with git" in done.err
    assert tree_hash(core) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == listing_before


# -- AC 25: what a clone must hold ------------------------------------------------------

@pytest.mark.parametrize("files, words", [
    ({"README.md": "no project\n"}, "has no TCW project at '.'"),
    (project_files("other"), "holds project 'other' at '.', not 'core'"),
    ({"tcw-config.yaml": "id: core\n"}, "TCW 3.x project"),
    ({".tcw/tcw-config.yaml": "tcw-version: 99.0.0\nid: core\n"}, "tcw-version"),
])
@pytest.mark.parametrize("place", ["../core", "../new/core"])
def test_ac25_a_clone_that_is_not_the_project(tmp_path, stand_in_git, files, words, place):
    remote = make_remote(tmp_path, "core", files)
    app = app_project(tmp_path, parents=["core"],
                      manifest={"core": {"path": place, "repository": str(remote)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert words in done.err, done.err
    assert not (tmp_path / "core").exists() and not (tmp_path / "new").exists()
    assert staging_left(tmp_path) == []


@pytest.mark.parametrize("repository", ["{tmp}/not-a-repository", "{remote}#nosuch"])
def test_ac25_a_clone_that_fails(tmp_path, stand_in_git, repository):
    remote = make_remote(tmp_path, "core", project_files("core"))
    (tmp_path / "not-a-repository").mkdir()
    url = repository.format(tmp=tmp_path, remote=remote)
    app = app_project(tmp_path, parents=["core"],
                      manifest={"core": {"path": "../new/core", "repository": url}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "git clone of" in done.err, done.err
    assert not (tmp_path / "new").exists()
    assert staging_left(tmp_path) == []


# -- AC 26: partial failure -------------------------------------------------------------

def test_ac26_what_was_fetched_stays(tmp_path, stand_in_git):
    aa = make_remote(tmp_path, "aa", project_files("aa"))
    bb = make_remote(tmp_path, "bb", project_files("bb"))
    app = app_project(tmp_path, parents=["aa", "bb"], manifest={
        "aa": {"path": "../aa", "repository": str(aa)},
        "bb": {"path": "../bb", "repository": str(bb)}})
    (tmp_path / "bb").mkdir()
    (tmp_path / "bb" / "f").write_text("")
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert done.err.splitlines()[-1] == ("fetched 1, failed 1; what was fetched stays, and "
                                         "running the command again fetches the rest")
    shutil.rmtree(tmp_path / "bb")
    stand_in_git.reset()
    assert provision(app).code == 0
    assert _cloned(stand_in_git) == ["bb"]


def test_ac26_a_failed_store_is_counted_and_the_projects_pass_runs(tmp_path, stand_in_git):
    aa = make_remote(tmp_path, "aa", project_files("aa"))
    bb = make_remote(tmp_path, "bb", project_files("bb"))
    app = app_project(tmp_path, parents=["aa", "bb"], manifest={
        "aa": {"path": "../aa", "repository": str(aa)},
        "bb": {"path": "../bb", "repository": str(bb)}})
    (tmp_path / "bb").mkdir()
    (tmp_path / "bb" / "f").write_text("")
    (app / "docs" / "work").rename(app / "docs" / "work-old")
    _declare_store(app, "work", str(tmp_path / "no-such-remote"))
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert done.err.splitlines()[-1].startswith("fetched 1, failed 2; "), done.err


def test_ac26_a_failed_store_still_runs_the_projects_pass(tmp_path, stand_in_git):
    app = make_project(tmp_path, "app")
    (app / "docs" / "work").rename(app / "docs" / "work-old")
    _declare_store(app, "work", str(tmp_path / "no-such-remote"))
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "nothing to fetch" in done.err, done.err
    assert done.err.splitlines()[-1].startswith("fetched 0, failed 1; "), done.err


# -- AC 27: the bound --------------------------------------------------------------------

def _ac27(tmp_path, base_path, *, personal_manifest=None):
    base = make_remote(tmp_path, "base", project_files("base"))
    files = project_files("core", parents=["base"], manifest={
        "base": {"path": base_path, "repository": str(base)}} if base_path else None)
    if personal_manifest is not None:
        from tests.provision_support import manifest_text
        files[".tcw/tcw-manifest.local.yaml"] = manifest_text(personal_manifest)
    core = make_remote(tmp_path, "core", files)
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../repos/core", "repository": str(core)}})
    (tmp_path / "repos").mkdir(exist_ok=True)
    return app, base


@pytest.mark.parametrize("base_path", ["../../base-far", "../x/base", "vendor/base",
                                       "../.base"])
def test_ac27_a_bounded_entry_outside_the_bound(tmp_path, stand_in_git, base_path):
    app, _ = _ac27(tmp_path, base_path)
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert _cloned(stand_in_git) == ["core"]
    repos = (tmp_path / "repos").resolve()
    assert f"outside {repos}; a manifest that is not this project's own" in done.err, done.err
    assert (tmp_path / "repos" / "core" / ".tcw").is_dir()
    assert not (tmp_path / "base-far").exists() and not (tmp_path / "repos" / "x").exists()
    assert not (tmp_path / "repos" / ".base").exists()
    assert not (tmp_path / "repos" / "core" / "vendor").exists()


def test_ac27_an_absolute_path_in_a_committed_personal_manifest(tmp_path, stand_in_git):
    app, base = _ac27(tmp_path, None, personal_manifest={
        "base": {"path": str((tmp_path / "repos" / "base").resolve()),
                 "repository": str(make_remote(tmp_path, "base2", project_files("base")))}})
    stand_in_git.allow_clone()
    done = provision(app, env=PERSONAL)
    assert done.code == 1, done
    assert "outside" in done.err and "a manifest that is not this project's own" in done.err
    assert not (tmp_path / "repos" / "base").exists()


def test_ac27_directly_inside_the_bound_is_fetched(tmp_path, stand_in_git):
    app, _ = _ac27(tmp_path, "../base")
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 0, done
    assert (tmp_path / "repos" / "base" / ".tcw").is_dir()


def test_ac27_every_run_and_the_way_out(tmp_path, stand_in_git):
    app, _ = _ac27(tmp_path, "../../base-far")
    stand_in_git.allow_clone()
    assert provision(app).code == 1
    again = provision(app)
    assert again.code == 1, again
    core = (tmp_path / "repos" / "core").resolve()
    assert f"tcw -C {core} project provision base" in again.err, again.err
    assert f"{core}/.tcw/tcw-manifest.local.yaml" in again.err, again.err
    assert str(app / ".tcw/tcw-manifest.local.yaml") not in again.err
    there = provision(core, "base")
    assert there.code == 0, there
    assert (tmp_path / "base-far" / ".tcw").is_dir()
    last = provision(app)
    assert last.code == 0 and "nothing to fetch" in last.err, last


def test_ac27_a_personal_entry_in_the_owner_places_it(tmp_path, stand_in_git):
    from tests.projectfiles import write_manifest as manifest
    app, base = _ac27(tmp_path, "../../base-far")
    stand_in_git.allow_clone()
    provision(app)
    core = tmp_path / "repos" / "core"
    manifest(core, {"base": {"path": str(tmp_path / "elsewhere" / "base"),
                             "repository": str(base)}}, local=True)
    done = provision(core, "base", env=PERSONAL)
    assert done.code == 0, done
    assert (tmp_path / "elsewhere" / "base" / ".tcw").is_dir()


@pytest.mark.parametrize("local", [True, False])
def test_ac27_trusted_entries_are_honoured(tmp_path, stand_in_git, local):
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = make_project(tmp_path / "w", "app")
    connect_projects(app, "parent", "core")
    place = str(tmp_path / "abs" / "core") if local else "../../far/core"
    write_manifest(app, {"core": {"path": place, "repository": str(remote)}}, local=local)
    stand_in_git.allow_clone()
    done = provision(app, env=PERSONAL)
    assert done.code == 0, done
    folder = tmp_path / ("abs" if local else "far") / "core"
    assert (folder / ".tcw").is_dir()


def _ws_case(tmp_path, *, git_file=False):
    wp = make_remote(tmp_path, "wp", project_files("wp"))
    ws = tmp_path / "ws"
    write_config(ws, "id: ws\n")
    write_manifest(ws, {"wp": {"path": "../x/wp", "repository": str(wp)}})
    if git_file:
        (ws / ".git").write_text(f"gitdir: {tmp_path / 'nowhere'}\n")
    app = app_project(tmp_path, parents=["ws", "wp"], manifest={"ws": "../ws"})
    return app


def test_ac27_a_manifest_already_here_is_bounded(tmp_path, stand_in_git):
    app = _ws_case(tmp_path)
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert f"outside {tmp_path.resolve()};" in done.err, done.err
    assert "in this project; they are read first" in done.err, done.err
    # Entries never merge (TCW-107 Design 2.2), so app's own entry gives the
    # repository too.
    write_manifest(app, {"wp": {"path": "../x/wp",
                                "repository": str(tmp_path / "remotes" / "wp.git")}},
                   local=True)
    (tmp_path / "x").mkdir()
    fixed = provision(app, env=PERSONAL)
    assert fixed.code == 0, fixed
    assert (tmp_path / "x" / "wp" / ".tcw").is_dir(), fixed


# -- AC 28: unfetchable projects ----------------------------------------------------------

def test_ac28_unfetchable_projects(tmp_path, stand_in_git):
    app = app_project(tmp_path, parents=["nn", "mm"], manifest={"mm": "../mm"})
    done = provision(app)
    assert done.code == 0, done
    assert done.err.count("no manifest entry gives the repository") == 2, done.err
    assert provision(app, "mm").code == 5
    nope = provision(app, "nope")
    assert nope.code == 1 and "check the spelling" in nope.err, nope
    assert provision(app, "Nope").code == 2


# -- AC 29: a worktree -------------------------------------------------------------------

def test_ac29_a_worktree_clones_next_to_the_main_checkout(tmp_path, stand_in_git):
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = app_project(tmp_path, parents=["core"],
                      manifest={"core": {"path": "../core", "repository": str(remote)}})
    real_git(app, "add", "-A")
    real_git(app, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "app")
    tree = tmp_path / "trees" / "app-w"
    tree.parent.mkdir()
    real_git(app, "worktree", "add", "-q", "-b", "w", str(tree))
    stand_in_git.allow_clone()
    done = provision(tree)
    assert done.code == 0, done
    assert (tmp_path / "core" / ".tcw").is_dir()
    path = tcw(tree, "project", "path", "core")
    assert path.out == f"{(tmp_path / 'core').resolve()}\n", path


# -- AC 30: the dry run ------------------------------------------------------------------

def test_ac30_the_dry_run_plans_the_first_round(tmp_path, ac20, stand_in_git):
    app, _ = ac20
    before = sorted(p.name for p in tmp_path.iterdir())
    done = provision(app, "--dry-run")
    assert done.code == 0, done
    assert stand_in_git.calls("clone") == []
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    core = (tmp_path / "core").resolve()
    assert f"core: would fetch into {core}" in done.err
    assert "core: any projects it names cannot be listed until it is fetched" in done.err
    assert "base" not in done.err


def test_ac30_the_dry_run_names_what_comes_with_a_clone(tmp_path, stand_in_git):
    app = _mono_app(tmp_path, _mono(tmp_path))
    done = provision(app, "--dry-run")
    assert done.code == 0, done
    assert "server: would fetch into" in done.err
    assert "client: would come with the clone for 'server'" in done.err


def test_ac30_the_dry_run_fails_as_the_run_would(tmp_path, ac19, stand_in_git):
    app, _ = ac19
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / ".git").write_text("gitdir: x\n")
    done = provision(app, "--dry-run")
    assert done.code == 1 and "holds only .git" in done.err, done
    assert stand_in_git.calls("clone") == []


def test_ac30_the_dry_run_applies_the_bound(tmp_path, stand_in_git):
    app = _ws_case(tmp_path)
    done = provision(app, "--dry-run")
    assert done.code == 1 and "outside" in done.err, done
    assert stand_in_git.calls("clone") == []


def test_ac30_the_dry_run_with_everything_here(tmp_path, stand_in_git):
    make_project(tmp_path, "core")
    app = app_project(tmp_path, parents=["core"])
    done = provision(app, "--dry-run")
    assert done.code == 0 and "nothing to fetch" in done.err and "would" not in done.err


# -- AC 31: graph problems first ---------------------------------------------------------

@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_ac31_a_manifest_problem_refuses_before_anything(tmp_path, stand_in_git, flags):
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../core", "repository": str(remote), "ref": "main"}})
    stand_in_git.allow_clone()
    done = provision(app, *flags)
    assert done.code == 1, done
    assert ".tcw/tcw-manifest.yaml" in done.err and "ref" in done.err, done.err
    assert stand_in_git.calls("clone") == []


@pytest.mark.parametrize("flags", [(), ("--dry-run",)])
def test_ac31_a_variable_naming_no_project(tmp_path, stand_in_git, flags):
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../core", "repository": str(remote)}})
    (tmp_path / "not-core").mkdir()
    stand_in_git.allow_clone()
    done = provision(app, *flags, env={"TCW_PROJECT_CORE": str(tmp_path / "not-core")})
    assert done.code == 1, done
    assert "TCW_PROJECT_CORE" in done.err, done.err
    assert stand_in_git.calls("clone") == []


# -- AC 32: a fetched project's own problem ----------------------------------------------

def test_ac32_a_fetched_manifest_with_a_problem(tmp_path, stand_in_git):
    base = make_remote(tmp_path, "base", project_files("base"))
    files = project_files("core", parents=["base"])
    from tests.provision_support import manifest_text
    files[".tcw/tcw-manifest.yaml"] = manifest_text(
        {"base": {"path": "../base", "repository": str(base), "ref": "x"}})
    core = make_remote(tmp_path, "core", files)
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../core", "repository": str(core)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    folder = (tmp_path / "core").resolve()
    assert f"core: fetched into {folder}, but" in done.err, done.err
    assert "tcw-manifest.yaml" in done.err and f"remove {folder} to undo" in done.err
    assert _cloned(stand_in_git) == ["core"]
    assert (folder / ".tcw").is_dir()


def test_ac32_the_refusal_names_the_project_with_the_problem(tmp_path, stand_in_git):
    """Two parents fetched in one round, the first with the problem: the
    refusal names that one and its folder, never the other (review round 1,
    finding 1)."""
    from tests.provision_support import manifest_text
    base = make_remote(tmp_path, "base", project_files("base"))
    files = project_files("aa", parents=["base"])
    files[".tcw/tcw-manifest.yaml"] = manifest_text(
        {"base": {"path": "../base", "repository": str(base), "ref": "x"}})
    aa = make_remote(tmp_path, "aa", files)
    bb = make_remote(tmp_path, "bb", project_files("bb"))
    app = app_project(tmp_path, parents=["aa", "bb"], manifest={
        "aa": {"path": "../aa", "repository": str(aa)},
        "bb": {"path": "../bb", "repository": str(bb)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert sorted(_cloned(stand_in_git)) == ["aa", "bb"]
    first, other = (tmp_path / "aa").resolve(), (tmp_path / "bb").resolve()
    assert f"aa: fetched into {first}, but" in done.err, done.err
    assert f"remove {first} to undo" in done.err, done.err
    assert "'aa' to .tcw/tcw-manifest.local.yaml" in done.err, done.err
    assert f"bb: fetched into {other}, but" not in done.err, done.err
    assert f"remove {other}" not in done.err, done.err


def test_ac32_the_refusal_names_each_project_with_a_problem(tmp_path, stand_in_git):
    """Two parents fetched in one round, each with a problem in its own
    manifest: the refusal names both, and each one's folder and entry."""
    from tests.provision_support import manifest_text
    base = make_remote(tmp_path, "base", project_files("base"))
    remotes = {}
    for name in ("aa", "bb"):
        files = project_files(name, parents=["base"])
        files[".tcw/tcw-manifest.yaml"] = manifest_text(
            {"base": {"path": "../base", "repository": str(base), "ref": "x"}})
        remotes[name] = make_remote(tmp_path, name, files)
    app = app_project(tmp_path, parents=["aa", "bb"], manifest={
        name: {"path": f"../{name}", "repository": str(remote)}
        for name, remote in remotes.items()})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert sorted(_cloned(stand_in_git)) == ["aa", "bb"]
    refusal = next(line for line in done.err.splitlines()
                   if line.startswith("tcw project provision: "))
    for name in ("aa", "bb"):
        folder = (tmp_path / name).resolve()
        assert f"{name}: fetched into {folder}" in refusal, refusal
        assert f"remove {folder}" in refusal, refusal
        assert f"'{name}'" in refusal and ".tcw/tcw-manifest.local.yaml" in refusal, refusal


def test_ac32_the_refusal_names_the_deeper_of_two_holders(tmp_path, stand_in_git):
    """`server` is in the clone made for `top`: a problem in `server`'s own
    manifest is `server`'s, though `top`'s folder holds it too. The clone is
    the folder whose removal undoes the fetch."""
    from tests.provision_support import manifest_text
    base = make_remote(tmp_path, "base", project_files("base"))
    files = project_files("server", at="apps/server", parents=["base"])
    files["apps/server/.tcw/tcw-manifest.yaml"] = manifest_text(
        {"base": {"path": "../../../base", "repository": str(base), "ref": "x"}})
    files.update(project_files("top"))
    mono = make_remote(tmp_path, "mono", files)
    app = app_project(tmp_path, parents=["top", "server"], manifest={
        "top": {"path": "../mono", "repository": str(mono)},
        "server": {"path": "../mono/apps/server", "repository": str(mono),
                   "subfolder": "apps/server"}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    clone = (tmp_path / "mono").resolve()
    assert f"server: fetched into {clone}, but" in done.err, done.err
    assert "'server' to .tcw/tcw-manifest.local.yaml" in done.err, done.err
    assert f"top: fetched into {clone}, but" not in done.err, done.err


def test_ac32_a_malformed_parents_is_a_warning(tmp_path, stand_in_git):
    core = make_remote(tmp_path, "core", project_files("core", parents=7))
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../core", "repository": str(core)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 0, done
    assert "warning: core: its parent links cannot be read" in done.err, done.err


# -- AC 34: a single project pays nothing ------------------------------------------------

def test_ac34_a_project_alone(tmp_path, stand_in_git):
    app = make_project(tmp_path, "solo")
    done = provision(app)
    assert done.code == 0, done
    assert done.err.splitlines() == [
        "Nothing to provision: no component declares a home repository in "
        ".tcw/tcw-config.yaml.",
        "nothing to fetch: every project it names is on this machine"], done.err
    assert stand_in_git.calls("clone") == []


# -- AC 35: a fetched manifest cannot move a project already here --------------------------

def test_ac35_a_kept_answer_that_changes_stops_the_run(tmp_path, stand_in_git):
    make_project(tmp_path, "lib")
    lib = make_remote(tmp_path, "lib", project_files("lib"))
    core = make_remote(tmp_path, "core", project_files("core", manifest={
        "lib": {"path": "../lib", "repository": str(lib)}}))
    app = app_project(tmp_path, parents=["core", "lib"], manifest={
        "core": {"path": "../repos/core", "repository": str(core)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert f"lib: was at {(tmp_path / 'lib').resolve()} when this run started" in done.err, done.err
    assert str((tmp_path / "repos" / "lib").resolve()) in done.err, done.err
    assert "repos/core/.tcw/tcw-manifest.yaml" in done.err, done.err
    assert _cloned(stand_in_git) == ["core"]
    assert not (tmp_path / "repos" / "lib").exists()
    write_manifest(app, {"lib": "../lib"}, local=True)
    again = provision(app, env=PERSONAL)
    assert again.code == 0 and "nothing to fetch" in again.err, again


@pytest.mark.parametrize("top, fetched", [("lib", False), ("mono", True)])
def test_ac35_a_clone_that_would_give_a_kept_project_a_second_folder(tmp_path, stand_in_git,
                                                                     top, fetched):
    make_project(tmp_path, "lib")
    remote = make_remote(tmp_path, "mono", {**project_files("server", at="apps/server"),
                                            **project_files(top)})
    app = app_project(tmp_path, parents=["lib", "server"], manifest={
        "server": {"path": "../mono/apps/server", "repository": str(remote),
                   "subfolder": "apps/server"}})
    stand_in_git.allow_clone()
    done = provision(app)
    if fetched:
        assert done.code == 0, done
        return
    assert done.code == 1, done
    assert f"holds project 'lib' at its top, but 'lib' is already at " \
           f"{(tmp_path / 'lib').resolve()}" in done.err, done.err
    assert not (tmp_path / "mono").exists()
    path = tcw(app, "project", "path", "lib")
    assert path.out == f"{(tmp_path / 'lib').resolve()}\n", path


# -- AC 36: resolved folders, the home folder, git -----------------------------------------

def test_ac36_a_a_committed_link_out_of_the_bound(tmp_path, stand_in_git):
    base = make_remote(tmp_path, "base", project_files("base"))
    files = project_files("core", parents=["base"], manifest={
        "base": {"path": "up/base", "repository": str(base)}})
    files["up"] = ("link", "../..")
    core = make_remote(tmp_path, "core", files)
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../repos/core", "repository": str(core)}})
    (tmp_path / "repos").mkdir()
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert f"places it at {(tmp_path / 'base').resolve()}, outside" in done.err, done.err
    assert not (tmp_path / "base").exists()


def test_ac36_a_a_committed_link_inside_the_bound(tmp_path, stand_in_git):
    base = make_remote(tmp_path, "base", project_files("base"))
    files = project_files("core", parents=["base"], manifest={
        "base": {"path": "lnk/base", "repository": str(base)}})
    files["lnk"] = ("link", "..")
    core = make_remote(tmp_path, "core", files)
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../repos/core", "repository": str(core)}})
    (tmp_path / "repos").mkdir()
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 0, done
    assert (tmp_path / "repos" / "base" / ".tcw").is_dir()


def test_ac36_b_a_folder_whose_text_begins_with_the_bound(tmp_path, stand_in_git):
    app, _ = _ac27(tmp_path, "../../repos-x/base")
    (tmp_path / "repos-x").mkdir()
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1 and "outside" in done.err, done
    assert not (tmp_path / "repos-x" / "base").exists()


@pytest.mark.parametrize("app_at, home_at", [("home/app", "home"),
                                             ("home/app", "home/inner"),
                                             ("home/.local/app", "home")])
def test_ac36_c_never_at_the_home_folder(tmp_path, stand_in_git, monkeypatch, app_at,
                                         home_at):
    home = tmp_path / home_at
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    base = make_remote(tmp_path, "base", project_files("base"))
    core = make_remote(tmp_path, "core", project_files("core", parents=["base"], manifest={
        "base": {"path": "../base", "repository": str(base)}}))
    app = app_project(tmp_path / Path(app_at).parent, parents=["core"], name="app",
                      manifest={"core": {"path": "../core", "repository": str(core)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert (app.parent / "core" / ".tcw").is_dir()
    assert "which is the home folder, a folder above it, or inside a hidden folder" \
        in done.err, done.err
    assert not (app.parent / "base").exists()


def test_ac36_d_a_link_committed_by_an_earlier_clone_of_the_round(tmp_path, stand_in_git):
    aa = make_remote(tmp_path, "aa", {**project_files("aa"), "l": ("link", "../../far/x")})
    bb = make_remote(tmp_path, "bb", project_files("bb"))
    core = make_remote(tmp_path, "core", project_files("core", parents=["aa", "bb"], manifest={
        "aa": {"path": "../aa", "repository": str(aa)},
        "bb": {"path": "../aa/l/../../bb", "repository": str(bb)}}))
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../repos/core", "repository": str(core)}})
    (tmp_path / "repos").mkdir()
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "bb" not in _cloned(stand_in_git)
    assert (tmp_path / "repos" / "aa" / ".tcw").is_dir()
    assert not (tmp_path / "bb").exists() and not (tmp_path / "far").exists()


def _ignores_case(folder: Path) -> bool:
    probe = folder / "case-probe-a"
    probe.mkdir()
    try:
        return (folder / "CASE-PROBE-A").exists()
    finally:
        probe.rmdir()


def test_ac36_e_letter_case_at_the_home_folder(tmp_path, stand_in_git, monkeypatch):
    if not _ignores_case(tmp_path):
        pytest.skip("this file system tells letter case apart")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    base = make_remote(tmp_path, "base", project_files("base"))
    core = make_remote(tmp_path, "core", project_files("core", parents=["base"], manifest={
        "base": {"path": "../base", "repository": str(base)}}))
    app = app_project(tmp_path / "w", parents=["core"])
    # `HOME` names `<tmp>/home`; the entry spells it `<tmp>/HOME`, so `core`'s
    # bound, the folder above it, is the home folder in other letters.
    upper = str(home.resolve().parent / "HOME" / "core")
    write_manifest(app, {"core": {"path": upper, "repository": str(core)}}, local=True)
    stand_in_git.allow_clone()
    done = provision(app, env=PERSONAL)
    assert done.code == 1, done
    assert (home / "core" / ".tcw").is_dir()
    assert "which is the home folder" in done.err, done.err


def test_ac36_e_two_names_that_differ_only_in_letter_case(tmp_path, stand_in_git):
    if not _ignores_case(tmp_path):
        pytest.skip("this file system tells letter case apart")
    aa = make_remote(tmp_path, "aa", project_files("aa"))
    bb = make_remote(tmp_path, "bb", project_files("bb"))
    core = make_remote(tmp_path, "core", project_files("core", parents=["aa", "bb"], manifest={
        "aa": {"path": "../Aa", "repository": str(aa)},
        "bb": {"path": "../aa", "repository": str(bb)}}))
    app = app_project(tmp_path, parents=["core"], manifest={
        "core": {"path": "../repos/core", "repository": str(core)}})
    (tmp_path / "repos").mkdir()
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "bb" not in _cloned(stand_in_git) and "aa" in _cloned(stand_in_git)
    assert "bb:" in done.err and "is not empty" in done.err, done.err


def test_ac36_f_git_cannot_say(tmp_path, stand_in_git):
    app = _ws_case(tmp_path, git_file=True)
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "git could not say which repository holds" in done.err, done.err


def test_ac36_g_a_subfolder_that_is_a_link(tmp_path, stand_in_git):
    make_project(tmp_path, "other")
    write_config(tmp_path / "other", "id: server\n")
    remote = make_remote(tmp_path, "mono", {"apps/server": ("link", "../../other"),
                                            "README.md": ""})
    app = app_project(tmp_path, parents=["server"], manifest={
        "server": {"path": "../mono/apps/server", "repository": str(remote),
                   "subfolder": "apps/server"}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "has a link at 'apps/server' that leads outside the clone" in done.err, done.err
    assert not (tmp_path / "mono").exists()


def test_ac36_g_a_tcw_folder_that_is_a_link(tmp_path, stand_in_git):
    make_project(tmp_path, "other")
    remote = make_remote(tmp_path, "mono", {"apps/server/.tcw": ("link", "../../../other/.tcw"),
                                            "README.md": ""})
    app = app_project(tmp_path, parents=["server"], manifest={
        "server": {"path": "../mono/apps/server", "repository": str(remote),
                   "subfolder": "apps/server"}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    assert "has a link at 'apps/server/.tcw'" in done.err, done.err


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("hooked", [True, False])
def test_ac36_h_git_location_variables_are_ignored(tmp_path, stand_in_git, hooked):
    mono = tmp_path / "mono"
    ws = mono / "packages" / "ws"
    write_config(ws, "id: ws\n")
    wp = make_remote(tmp_path, "wp", project_files("wp"))
    wq = make_remote(tmp_path, "wq", project_files("wq"))
    write_manifest(ws, {"wp": {"path": "../../../wp", "repository": str(wp)},
                        "wq": {"path": "../wq", "repository": str(wq)}})
    real_git(mono, "init", "-q")
    real_git(mono, "add", "-A")
    real_git(mono, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "mono")
    app = tmp_path / "app"
    write_config(app, "id: app\nparents: [ws, wp, wq]\n")
    write_manifest(app, {"ws": "../mono/packages/ws"})
    before = (_hash(mono / ".git" / "index"), _hash(mono / ".git" / "HEAD"))
    env = {"GIT_DIR": str(mono / ".git"),
           "GIT_INDEX_FILE": str(mono / ".git" / "index")} if hooked else None
    stand_in_git.allow_clone()
    done = provision(app, env=env)
    assert done.code == 1, done
    assert (tmp_path / "wp" / ".tcw").is_dir()
    assert f"wq: " in done.err and f"outside {tmp_path.resolve()};" in done.err, done.err
    assert (_hash(mono / ".git" / "index"), _hash(mono / ".git" / "HEAD")) == before


def test_ac36_j_an_owner_in_the_active_projects_worktree(tmp_path, stand_in_git):
    mono = tmp_path / "mono"
    write_config(mono / "packages" / "app", "id: app\nparents: [ws, wp]\n")
    write_config(mono / "packages" / "ws", "id: ws\n")
    wp = make_remote(tmp_path, "wp", project_files("wp"))
    write_manifest(mono / "packages" / "ws",
                   {"wp": {"path": "../../../wp", "repository": str(wp)}})
    real_git(mono, "init", "-q")
    real_git(mono, "add", "-A")
    real_git(mono, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "mono")
    tree = mono / ".claude" / "worktrees" / "w"
    real_git(mono, "worktree", "add", "-q", "-b", "w", str(tree))
    stand_in_git.allow_clone()
    done = provision(tree / "packages" / "app")
    assert done.code == 0, done
    assert (tmp_path / "wp" / ".tcw").is_dir()


# -- AC 37: staging copies and addresses that look like options ----------------------------

def test_ac37_a_leftover_staging_copy_is_left_alone(tmp_path, ac19):
    app, _ = ac19
    left = tmp_path / ".tcw-staging-0123abcd" / "core"
    shutil.copytree(make_project(tmp_path / "spare", "core"), left)
    before = tree_hash(left.parent)
    done = provision(app)
    assert done.code == 0, done
    assert (tmp_path / "core" / ".tcw").is_dir()
    assert tree_hash(left.parent) == before


@pytest.mark.parametrize("repository", ["--template={tmp}/t", "{remote}#--orphan"])
def test_ac37_an_address_that_looks_like_an_option(tmp_path, stand_in_git, repository):
    remote = make_remote(tmp_path, "core", project_files("core"))
    app = app_project(tmp_path, parents=["core"], manifest={"core": {
        "path": "../core", "repository": repository.format(tmp=tmp_path, remote=remote)}})
    stand_in_git.allow_clone()
    done = provision(app)
    assert done.code == 1, done
    # TCW-107's manifest reader refuses it first, as a graph problem (7.14);
    # 7.9's own `-` check is unit-tested in tests/test_fetch_project.py.
    assert "tcw-manifest.yaml: projects.core: repository" in done.err, done.err
    assert "must not begin with '-'" in done.err, done.err
    assert stand_in_git.calls("clone") == []


# -- the stand-in git itself ------------------------------------------------------------

def test_the_stand_in_refuses_a_clone_unless_allowed(tmp_path, stand_in_git):
    import subprocess
    remote = make_remote(tmp_path, "r", {"f": ""})
    refused = subprocess.run(["git", "clone", "-q", str(remote), str(tmp_path / "c1")],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert refused.returncode == 97 and "stand-in git: network call" in refused.stderr
    assert not (tmp_path / "c1").exists()
    stand_in_git.allow_clone()
    allowed = subprocess.run(["git", "clone", "-q", str(remote), str(tmp_path / "c2")],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert allowed.returncode == 0 and (tmp_path / "c2" / "f").exists()
    passed = subprocess.run(["git", "-C", str(tmp_path / "c2"), "rev-parse", "HEAD"],
                            capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert passed.returncode == 0
    assert [call[0] for call in stand_in_git.calls()] == ["clone", "clone", "-C"]


# -- AC 38: another project's store names the command run there ----------------------------

def test_ac38_another_projects_store(tmp_path):
    from tests.projectfiles import write_config_file
    import yaml
    core = make_project(tmp_path, "core")
    document = yaml.safe_load(config_file(core).read_text())
    document["taxonomy"] = {"path": "terms",
                            "repository": {"url": "https://example.invalid/terms.git"}}
    write_config_file(config_file(core), yaml.safe_dump(document, sort_keys=False))
    app = app_project(tmp_path, parents=["core"])
    from tcw.store.fs import init
    init(["taxonomy"], app)
    # TCW-113 Design 4.9 makes the default scope, `own`, read `app`'s own
    # declarations without its view (warning, exit 0); a scope that needs the
    # view stops with exit 7. Both carry the command run in `core`'s folder.
    # Decided by the implementing agent in implement round 3.
    fetch = (f"tcw -C {core.resolve()} project provision --component taxonomy",
             f"tcw -C {core} project provision --component taxonomy")
    own = tcw(app, "taxonomy", "list")
    assert own.code == 0, own
    assert any(text in own.err for text in fetch), own.err
    shown = tcw(app, "taxonomy", "list", "--scope", "up")
    assert shown.code == 7, shown
    assert any(text in shown.err for text in fetch), shown.err
    there = tcw(core, "taxonomy", "list")
    assert "tcw project provision --component taxonomy" in there.err, there
    assert "tcw -C" not in there.err


def test_ac32_no_fetched_project_holds_the_file(tmp_path):
    """Design 7.11's general text when the problem is in no fetched project's
    folder: `_holders` names none."""
    from types import SimpleNamespace

    from tcw.provision import Planned, _holders
    (tmp_path / "core").mkdir()
    core = Planned("core", SimpleNamespace(entry_folder=tmp_path / "core"),
                   tmp_path / "core", True)
    assert _holders([core], [tmp_path / "app/.tcw/tcw-manifest.yaml"]) == []
    assert _holders([core], [tmp_path / "core/.tcw/tcw-manifest.yaml"]) == [core]
