"""Opening backends, and delegating into another project (TCW-70 Design 2, 3.5,
6; the library half of AC 9 and AC 20)."""

import os
import shutil

import pytest
import yaml

from tcw.errors import BackendError, NotFound, Refused, Unreachable
from tcw.work.backend import Query
from tcw.work.config import MIGRATION_GUIDE
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.open import (
    delegate, open_backend, open_for_update, open_project, uncommitted_changes,
)
from tcw.work.model import Changes
from tests.work.projects import commit_all, connect, git, make_project


def write_config(root, **document):
    path = root / "tcw-config.yaml"
    data = yaml.safe_load(path.read_text())
    data.update(document)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


# -- open_backend (AC 20, library) ---------------------------------------------------

def test_open_backend_gives_the_filesystem_backend(tmp_path):
    p = make_project(tmp_path, "p")
    backend = open_backend(p)
    assert isinstance(backend, FsWorkBackend)
    assert backend.project == "p"
    assert backend.work_path == (p / "docs" / "work").resolve()


def test_a_removed_key_names_the_key_and_the_guide(tmp_path):
    p = make_project(tmp_path, "p", config={"tracker": {"provider": "jira-cloud"}})
    with pytest.raises(BackendError) as error:
        open_backend(p)
    assert "work.tracker" in str(error.value)
    assert MIGRATION_GUIDE in str(error.value)


def test_the_jira_backend_is_not_here_yet(tmp_path):
    statuses = ["inbox", "request", "spec", "plan", "implement", "review", "qa",
                "completed", "discarded"]
    p = make_project(tmp_path, "p", config={
        "backend": "jira", "jira": {},
        "stages": {name: {"status": name.title()} for name in statuses}})
    with pytest.raises(BackendError, match="TCW-71"):
        open_backend(p)


def test_no_work_path_is_an_error(tmp_path):
    p = make_project(tmp_path, "p")
    shutil.rmtree(p / "docs" / "work")
    with pytest.raises(BackendError):
        open_backend(p)


def test_an_empty_work_path_is_a_store(tmp_path):
    p = make_project(tmp_path, "p")
    (p / "docs" / "work" / ".gitkeep").unlink()
    assert open_backend(p).list(Query()) == []


# -- open_project -----------------------------------------------------------------------

@pytest.fixture
def pq(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    commit_all(p)
    commit_all(q)
    return p, q


def test_open_project_reads_another_project(pq):
    p, q = pq
    assert open_project("q", p).project == "q"


def test_open_project_not_declared_and_absent(pq):
    p, q = pq
    with pytest.raises(NotFound):
        open_project("nobody", p)
    shutil.rmtree(q)
    with pytest.raises(Unreachable):
        open_project("q", p)


# -- delegate and open_for_update (AC 9, library) ------------------------------------------

def state(root):
    return (git(root, "rev-parse", "HEAD"), git(root, "status", "--porcelain",
                                                "--untracked-files=all"))


def test_delegate_creates_an_inbox_item_and_commits_nothing(pq):
    p, q = pq
    before = state(q)
    lines = []
    slug = delegate("q", "T", "please\n", "high", here=p, report=lines.append)
    folder = slug.split("/", 1)[1]
    assert slug.startswith("q/") and folder.endswith("-t")
    item = yaml.safe_load((q / "docs" / "work" / folder / "item.yaml").read_text())
    assert item == {"title": "T", "stage": "inbox", "priority": "high"}
    assert any("item.yaml" in l and "uncommitted" in l for l in lines)
    assert git(q, "rev-parse", "HEAD") == before[0]
    assert git(q, "diff", "--cached", "--name-only") == ""


def assert_refused_and_nothing_written(q, call, match):
    before = state(q) if (q / ".git").exists() else None
    folders = sorted(os.listdir(q / "docs" / "work")) if (q / "docs" / "work").is_dir() else None
    with pytest.raises(Refused, match=match):
        call()
    if before is not None:
        assert state(q) == before
    if folders is not None:
        assert sorted(os.listdir(q / "docs" / "work")) == folders


def test_an_undeclared_id_is_refused(pq):
    p, q = pq
    with pytest.raises(Refused, match="no project 'nobody'"):
        delegate("nobody", "T", None, None, here=p)


def test_an_upstream_project_is_read_only(tmp_path):
    p = make_project(tmp_path, "p")
    r = make_project(tmp_path, "r")
    connect(p, r, "upstream")
    commit_all(r)
    assert_refused_and_nothing_written(
        r, lambda: delegate("r", "T", None, None, here=p), "read-only")
    with pytest.raises(Refused, match="read-only"):
        open_for_update("r", p)


def test_an_absent_upstream_with_a_jira_block_is_still_upstream(tmp_path):
    p = make_project(tmp_path, "p")
    write_config(p, **{"connected-projects": {"upstream": {
        "r": {"path": "../r", "jira": {"site": "x"}}}}})
    with pytest.raises(Refused, match="read-only"):
        delegate("r", "T", None, None, here=p)


def test_a_declared_absent_project_is_refused(pq):
    p, q = pq
    shutil.rmtree(q)
    with pytest.raises(Refused, match="not on this machine"):
        delegate("q", "T", None, None, here=p)


def test_an_absent_project_with_a_jira_block(pq):
    p, q = pq
    shutil.rmtree(q)
    write_config(p, **{"connected-projects": {"children": {
        "q": {"path": "../q", "jira": {"site": "x"}}}}})
    with pytest.raises(BackendError, match="Jira delegation arrives with the Jira backend"):
        delegate("q", "T", None, None, here=p)
    with pytest.raises(Refused):
        open_for_update("q", p)


def test_a_missing_work_store_is_refused(pq):
    p, q = pq
    shutil.rmtree(q / "docs" / "work")
    commit_all(q)
    assert_refused_and_nothing_written(
        q, lambda: delegate("q", "T", None, None, here=p), "no work store")


def test_uncommitted_changes_are_refused(pq):
    p, q = pq
    (q / "docs" / "work" / "stray.md").write_text("x")
    assert_refused_and_nothing_written(
        q, lambda: delegate("q", "T", None, None, here=p), "uncommitted changes")


def test_a_refused_delegation_does_not_touch_the_index(pq):
    p, q = pq
    (q / "docs" / "work" / "stray.md").write_text("x")
    index = q / ".git" / "index"
    before = index.stat().st_mtime_ns
    with pytest.raises(Refused):
        delegate("q", "T", None, None, here=p)
    assert index.stat().st_mtime_ns == before


def test_open_for_update_follows_the_same_conditions(pq):
    p, q = pq
    target = open_for_update("q", p)
    item = target.create("x", Changes(), stage="request", request=None)
    commit_all(q)
    open_for_update("q", p).update(item.slug.folder,
                                   Changes(add_blocked_by=("p/2026-01-01-a",)))
    (q / "docs" / "work" / "stray.md").write_text("x")
    with pytest.raises(Refused, match="uncommitted"):
        open_for_update("q", p)


# -- uncommitted_changes ---------------------------------------------------------------------

def test_uncommitted_changes(tmp_path):
    q = make_project(tmp_path, "q")
    (q / ".gitignore").write_text("*.log\n")
    commit_all(q)
    work = q / "docs" / "work"
    assert uncommitted_changes(work) == []
    (work / "debug.log").write_text("ignored")
    assert uncommitted_changes(work) == []
    (work / "new.md").write_text("x")
    assert uncommitted_changes(work) == ["docs/work/new.md"]


def test_a_store_outside_git_cannot_be_checked(tmp_path):
    outside = tmp_path / "plain"
    outside.mkdir()
    with pytest.raises(Refused, match="not in a git repository"):
        uncommitted_changes(outside, "q")
