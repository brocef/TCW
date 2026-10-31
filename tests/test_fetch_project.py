"""The library half of `tcw project provision` (TCW-115 plan, Steps 13 to 15):
`fetch_project`'s steps (plan choice 9), the bound (choice 8), git's answer
about a repository's top (choice 24), and the kept answers' message (7.4).

Each test names the part of the plan it pins. Every remote is a bare
repository in the test's own folder; no test reaches the network.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tcw import provision
from tcw.provision import (RepositoryUnknown, _bound_problem, _changed_answer,
                           _dash_problem, _Run, repository_top)
from tcw.store import fs
from tcw.store.fs import FetchRefused, fetch_project
from tests.provision_support import make_remote, project_files, real_git


def staging_left(folder: Path) -> list[Path]:
    return sorted(folder.glob(".tcw-staging-*"))


@pytest.fixture
def remote(tmp_path):
    return make_remote(tmp_path, "core", project_files("core"))


def fetch(remote, target, **kwargs):
    kwargs.setdefault("project_id", "core")
    return fetch_project(str(remote), kwargs.pop("branch", None), target, **kwargs)


def test_a_fetch_lands_at_the_target_and_leaves_no_staging(tmp_path, remote):
    target = tmp_path / "core"
    fetch(remote, target)
    assert (target / ".tcw" / "tcw-config.yaml").is_file()
    assert staging_left(tmp_path) == []


# -- step 7: the move ------------------------------------------------------------------

def test_step7_a_move_that_fails(tmp_path, remote, monkeypatch):
    def failing(*args, **kwargs):
        raise OSError(13, "Permission denied")
    monkeypatch.setattr(fs.os, "rename", failing)
    target = tmp_path / "core"
    with pytest.raises(FetchRefused, match=r"core: could not move the clone into .*core: "
                                           r"Permission denied"):
        fetch(remote, target)
    assert not os.path.lexists(target)
    assert staging_left(tmp_path) == []


# -- step 6: the folder checked again just before the move ------------------------------

def test_step6_a_file_appearing_before_the_move(tmp_path, remote):
    target = tmp_path / "core"

    def appear():
        target.mkdir()
        (target / "f").write_text("mine\n")
        return target
    with pytest.raises(FetchRefused, match="is not empty"):
        fetch(remote, target, recheck=appear)
    assert [p.name for p in target.iterdir()] == ["f"]
    assert staging_left(tmp_path) == []


def test_step6_a_link_put_at_the_folders_name(tmp_path, remote):
    target = tmp_path / "core"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    def link():
        target.symlink_to(elsewhere)
        return target
    with pytest.raises(FetchRefused, match="is not empty"):
        fetch(remote, target, recheck=link)
    assert list(elsewhere.iterdir()) == []
    assert target.is_symlink()


def test_step6_the_entry_now_leads_elsewhere(tmp_path, remote):
    target = tmp_path / "core"
    other = tmp_path / "other"
    with pytest.raises(FetchRefused, match=r"core: \.\./core led to .*core when this round "
                                           r"was checked, and now leads to .*other"):
        fetch(remote, target, recheck=lambda: other, written="../core")
    assert not target.exists() and not other.exists()
    assert staging_left(tmp_path) == []


# -- step 3: the staging name ------------------------------------------------------------

def test_step3_a_taken_staging_name_is_never_written_into(tmp_path, remote, monkeypatch):
    taken = tmp_path / ".tcw-staging-0123abcd"
    taken.mkdir()
    (taken / "theirs").write_text("x\n")
    names = iter(["0123abcd", "89abcdef"])
    monkeypatch.setattr(fs.secrets, "token_hex", lambda n: next(names))
    fetch(remote, tmp_path / "core")
    assert [p.name for p in taken.iterdir()] == ["theirs"]
    assert (tmp_path / "core" / ".tcw").is_dir()
    assert staging_left(tmp_path) == [taken]


def test_step3_five_taken_names_refuse(tmp_path, remote, monkeypatch):
    taken = tmp_path / ".tcw-staging-0123abcd"
    taken.mkdir()
    monkeypatch.setattr(fs.secrets, "token_hex", lambda n: "0123abcd")
    with pytest.raises(FetchRefused, match="five names in a row were already taken"):
        fetch(remote, tmp_path / "core")
    assert staging_left(tmp_path) == [taken]
    assert not (tmp_path / "core").exists()


# -- step 8: the staging folder removed ---------------------------------------------------

@pytest.mark.parametrize("fetched", [True, False])
def test_step8_a_staging_folder_that_cannot_be_removed(tmp_path, remote, monkeypatch,
                                                       fetched):
    real = shutil.rmtree
    monkeypatch.setattr(fs.shutil, "rmtree",
                        lambda path, *a, **k: (_ for _ in ()).throw(OSError(16, "Busy")))
    warnings = []
    url = remote if fetched else tmp_path / "no-remote"
    try:
        if fetched:
            fetch(url, tmp_path / "core", warn=warnings.append)
        else:
            with pytest.raises(FetchRefused, match="git clone of"):
                fetch(url, tmp_path / "core", warn=warnings.append)
    finally:
        monkeypatch.setattr(fs.shutil, "rmtree", real)
    [line] = warnings
    [left] = staging_left(tmp_path)
    assert line == f"could not remove the staging folder {left}: Busy; remove it by hand"
    assert (tmp_path / "core" / ".tcw").is_dir() is fetched


# -- steps 1 and 8: a trusted entry's missing parents -------------------------------------

def test_step1_missing_parents_are_made_and_removed_on_a_refusal(tmp_path):
    target = tmp_path / "a" / "b" / "c" / "core"
    with pytest.raises(FetchRefused):
        fetch(tmp_path / "no-remote", target)
    assert not (tmp_path / "a").exists()


def test_step1_a_made_parent_that_gained_an_entry_is_left(tmp_path, monkeypatch):
    target = tmp_path / "a" / "b" / "core"
    real = fs._git

    def clone_then_fail(argv, **kwargs):
        (tmp_path / "a" / "theirs").write_text("")
        return real(argv, **kwargs)
    monkeypatch.setattr(fs, "_git", clone_then_fail)
    with pytest.raises(FetchRefused):
        fetch(tmp_path / "no-remote", target)
    assert not (tmp_path / "a" / "b").exists()
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == ["theirs"]


def test_step1_a_bounded_entry_makes_no_parent(tmp_path, remote):
    with pytest.raises(FetchRefused, match="cannot open"):
        fetch(remote, tmp_path / "missing" / "core", trusted=False, bound=tmp_path)
    assert not (tmp_path / "missing").exists()


def test_step2_the_held_parent_must_be_the_bound(tmp_path, remote):
    (tmp_path / "x").mkdir()
    with pytest.raises(FetchRefused, match="is no longer the folder directly inside"):
        fetch(remote, tmp_path / "x" / "core", trusted=False, bound=tmp_path)
    assert list((tmp_path / "x").iterdir()) == []


# -- step 4: the clone's argv ---------------------------------------------------------------

@pytest.mark.parametrize("branch", ["main", None])
def test_step4_the_clone_argv(tmp_path, remote, monkeypatch, branch):
    calls = []
    real = fs._git

    def recording(argv, **kwargs):
        calls.append(list(argv))
        return real(argv, **kwargs)
    monkeypatch.setattr(fs, "_git", recording)
    fetch(remote, tmp_path / "core", branch=branch)
    # `_no_prompt_env` reads `core.sshCommand` first; the clone is the only other call.
    [clone] = [c for c in calls if c[1] == "clone"]
    with_branch = ["--branch", "main"] if branch else []
    assert clone[:-1] == ["git", "clone", "--quiet", *with_branch, "--", str(remote)], clone
    assert Path(clone[-1]).parent.name.startswith(".tcw-staging-")
    assert [c[1] for c in calls] == ["config", "clone"], calls


# -- step 5: the clone checked, never through a link out of it ----------------------------

def _never_read(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a configuration was read")
    monkeypatch.setattr(fs.yaml, "safe_load", refuse)


@pytest.mark.parametrize("files, subfolder, link", [
    ({"apps/server": ("link", "../../outside"), "README.md": ""}, "apps/server",
     "apps/server"),
    ({"apps/server/.tcw": ("link", "../../../outside/.tcw"), "README.md": ""},
     "apps/server", "apps/server/.tcw"),
    ({".tcw/tcw-config.yaml": ("link", "../../outside/.tcw/tcw-config.yaml")}, None,
     ".tcw/tcw-config.yaml"),
    ({**project_files("server", at="apps/server"), ".tcw": ("link", "../outside/.tcw")},
     "apps/server", ".tcw"),
])
def test_step5_a_link_out_of_the_clone(tmp_path, monkeypatch, files, subfolder, link):
    outside = tmp_path / "remote-work" / "outside"
    (outside / ".tcw").mkdir(parents=True)
    (outside / ".tcw" / "tcw-config.yaml").write_text("id: server\n")
    remote = make_remote(tmp_path, "mono", files)
    _never_read(monkeypatch)
    target = tmp_path / "mono"
    with pytest.raises(FetchRefused, match=f"has a link at '{link}' that leads outside "
                                           f"the clone"):
        fetch(remote, target, project_id="server", subfolder=subfolder)
    assert not target.exists()


def test_step5_a_link_inside_the_clone_is_followed(tmp_path):
    remote = make_remote(tmp_path, "mono", {**project_files("server", at="real/server"),
                                            "apps": ("link", "real")})
    fetch(remote, tmp_path / "mono", project_id="server", subfolder="apps/server")
    assert (tmp_path / "mono" / "apps" / "server" / ".tcw").is_dir()


@pytest.mark.parametrize("url, branch, refused", [
    ("--template=/x", None, True), ("/r.git", "--orphan", True), ("/r.git", "main", False),
    ("/r-.git", "a-b", False)])
def test_the_dash_check(url, branch, refused):
    placement = SimpleNamespace(id="core", entry=SimpleNamespace(
        url=url, branch=branch, file="/p/.tcw/tcw-manifest.yaml"))
    problem = _dash_problem(placement)
    assert (problem == "core: /p/.tcw/tcw-manifest.yaml gives a repository beginning "
                       "with '-'") is refused
    assert (problem is None) is not refused


# -- the bound (plan choice 8) ----------------------------------------------------------

def _placement(owner: Path, path: str, *, asked_by: Path | None = None, pid="base"):
    written = Path(path).expanduser()
    return SimpleNamespace(
        id=pid, asked_by=asked_by or owner, owner=owner,
        entry=SimpleNamespace(path=path, file=owner / ".tcw" / "tcw-manifest.yaml",
                              subfolder=None, url="/r.git", branch=None),
        repository_path=owner / written)


def _owner(tmp_path, *parts) -> Path:
    folder = tmp_path.joinpath(*parts)
    folder.mkdir(parents=True)
    return folder


@pytest.fixture
def home(tmp_path_factory):
    return tmp_path_factory.mktemp("home")


def test_bound_the_owner_is_the_active_project(tmp_path, home):
    app = _owner(tmp_path, "w", "app")
    problem, target, trusted, bound = _bound_problem(_placement(app, "../../far/base"),
                                                     app, {}, home)
    assert (problem, trusted, bound) == (None, True, None)
    assert target == Path(os.path.realpath(tmp_path / "far" / "base"))


def test_bound_directly_inside_is_allowed(tmp_path, home):
    core = _owner(tmp_path, "repos", "core")
    active = _owner(tmp_path, "app")
    problem, target, trusted, bound = _bound_problem(_placement(core, "../base"), active,
                                                     {}, home)
    assert problem is None and trusted is False
    assert bound == Path(os.path.realpath(tmp_path / "repos"))
    assert target == bound / "base"


def test_bound_the_as_written_rule(tmp_path, home):
    core = _owner(tmp_path, "repos", "core")
    active = _owner(tmp_path, "app")
    inside = str(Path(os.path.realpath(tmp_path / "repos")) / "base")
    problem, target, _, _ = _bound_problem(_placement(core, inside), active, {}, home)
    assert target is None and "a manifest that is not this project's own" in problem


def test_bound_the_strict_resolution(tmp_path, home):
    core = _owner(tmp_path, "repos", "core")
    active = _owner(tmp_path, "app")
    problem, target, _, _ = _bound_problem(_placement(core, "../nowhere/../base"), active,
                                           {}, home)
    assert target is None and "outside" in problem, problem


def test_bound_hidden_below_home(tmp_path, monkeypatch):
    home = _owner(tmp_path, "home")
    core = _owner(tmp_path, "home", ".local", "x", "core")
    active = _owner(tmp_path, "app")
    problem, target, _, _ = _bound_problem(_placement(core, "../base"), active, {}, home)
    assert target is None and "inside a hidden folder below it" in problem, problem


@pytest.mark.parametrize("at", ["home", "home/inner"])
def test_bound_at_or_above_home(tmp_path, at):
    home = _owner(tmp_path, *at.split("/"))
    core = _owner(tmp_path, "home", "core")
    active = _owner(tmp_path, "app")
    problem, target, _, _ = _bound_problem(_placement(core, "../base"), active, {}, home)
    assert target is None and "which is the home folder" in problem, problem


def test_bound_an_owner_cloned_in_this_run(tmp_path, home):
    repo = _owner(tmp_path, "repos", "mono")
    owner = _owner(tmp_path, "repos", "mono", "apps", "ws")
    active = _owner(tmp_path, "app")
    problem, target, _, bound = _bound_problem(_placement(owner, "../../../base"), active,
                                               {"ws": repo}, home)
    assert problem is None and bound == Path(os.path.realpath(tmp_path / "repos"))


def test_bound_the_linked_worktree_rule(tmp_path, home):
    mono = _owner(tmp_path, "mono")
    (mono / "packages" / "ws").mkdir(parents=True)
    (mono / "packages" / "ws" / "f").write_text("")
    real_git(mono, "init", "-q")
    real_git(mono, "add", "-A")
    real_git(mono, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "one")
    tree = mono / ".claude" / "worktrees" / "w"
    real_git(mono, "worktree", "add", "-q", "-b", "w", str(tree))
    owner = tree / "packages" / "ws"
    placement = _placement(owner, "../../../wp")
    placement.repository_path = mono / "packages" / "ws" / "../../../wp"
    problem, target, _, bound = _bound_problem(placement, tree / "packages", {}, home)
    assert problem is None, problem
    assert bound == Path(os.path.realpath(tmp_path))


# -- repository_top (plan choice 24) ------------------------------------------------------

def _repository(folder: Path) -> Path:
    (folder / "packages" / "p").mkdir(parents=True)
    real_git(folder, "init", "-q")
    return folder


def test_repository_top_with_no_git_above(tmp_path):
    assert repository_top(_owner(tmp_path, "plain")) is None


def test_repository_top_from_git(tmp_path):
    w = _repository(tmp_path / "w")
    assert repository_top(w / "packages" / "p") == Path(os.path.realpath(w))


def test_repository_top_when_git_fails(tmp_path):
    folder = _owner(tmp_path, "ws")
    (folder / ".git").write_text(f"gitdir: {tmp_path / 'nowhere'}\n")
    with pytest.raises(RepositoryUnknown):
        repository_top(folder)


def test_repository_top_with_no_git_installed(tmp_path, monkeypatch):
    w = _repository(tmp_path / "w")
    empty = _owner(tmp_path, "no-git")
    monkeypatch.setenv("PATH", str(empty))
    with pytest.raises(RepositoryUnknown, match="git is not installed"):
        repository_top(w)


@pytest.mark.parametrize("variable", ["GIT_DIR", "GIT_CEILING_DIRECTORIES"])
def test_repository_top_ignores_the_location_variables(tmp_path, monkeypatch, variable):
    w = _repository(tmp_path / "w")
    monkeypatch.setenv(variable, str(w / ".git") if variable == "GIT_DIR" else str(w))
    assert repository_top(w / "packages" / "p") == Path(os.path.realpath(w))


def test_ac36_i_a_submodule_is_its_own_repository(tmp_path, home):
    ws_remote = make_remote(tmp_path, "ws", project_files("ws"))
    sup = tmp_path / "sup"
    sup.mkdir()
    real_git(sup, "init", "-q")
    subprocess.run(["git", "-C", str(sup), "-c", "protocol.file.allow=always", "submodule",
                    "add", "-q", str(ws_remote), "vendor/ws"], check=True,
                   capture_output=True, stdin=subprocess.DEVNULL)
    ws = sup / "vendor" / "ws"
    assert repository_top(ws) == Path(os.path.realpath(ws))
    active = _owner(tmp_path, "app")
    problem, _, _, bound = _bound_problem(_placement(ws, "../x"), active, {}, home)
    assert problem is None and bound == Path(os.path.realpath(sup / "vendor"))
    problem, _, _, _ = _bound_problem(_placement(ws, "../../x"), active, {}, home)
    assert f"outside {Path(os.path.realpath(sup / 'vendor'))};" in problem, problem


# -- the check made again before each clone ------------------------------------------------

def test_the_round_is_checked_again_before_each_clone(tmp_path, monkeypatch):
    first = provision.Planned("core", SimpleNamespace(
        id="core", entry=SimpleNamespace(path="../core", url="/r.git", branch=None,
                                         file="/m")), tmp_path / "core", True)
    moved = provision.Planned("core", first.placement, tmp_path / "other", True)
    monkeypatch.setattr(provision, "_check", lambda placement, run: (None, moved))
    monkeypatch.setattr(fs, "fetch_project",
                        lambda *a, **k: pytest.fail("a clone was attempted"))
    lines = []
    run = _Run(root=tmp_path, prefix="tcw project provision", home=tmp_path)
    run.say = run.refuse = lines.append
    assert provision._fetch(first, tmp_path, run) is False
    [line] = lines
    assert line == (f"core: ../core led to {tmp_path / 'core'} when this round was "
                    f"checked, and now leads to {tmp_path / 'other'}; nothing was fetched "
                    f"for it")


# -- Design 7.4's fallback text ----------------------------------------------------------

def test_the_kept_answer_message_without_an_entry(tmp_path):
    moved = SimpleNamespace(folder=tmp_path / "new", entry=None, entry_folder=None)
    registry = SimpleNamespace(placement=lambda pid, asked_by: moved,
                               entry_elsewhere=lambda pid, asked_by: None)
    run = _Run(root=tmp_path / "app", prefix="p", home=tmp_path)
    run.kept["lib"] = (tmp_path / "lib", tmp_path / "app")
    assert _changed_answer(registry, run) == (
        f"lib: was at {tmp_path / 'lib'} when this run started, but this run's fetches now "
        f"places it at {tmp_path / 'new'}; add an entry for 'lib' to "
        f".tcw/tcw-manifest.local.yaml in {tmp_path / 'app'}, which that lookup reads "
        f"first, to keep it where it is")


def test_an_unchanged_kept_answer_is_no_message(tmp_path):
    same = SimpleNamespace(folder=tmp_path, entry=None, entry_folder=None)
    registry = SimpleNamespace(placement=lambda pid, asked_by: same)
    run = _Run(root=tmp_path, prefix="p", home=tmp_path)
    run.kept["lib"] = (tmp_path, tmp_path)
    assert _changed_answer(registry, run) is None
