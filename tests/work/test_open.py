"""Opening backends, and reading another project (TCW-70 Design 2, 3.5; the
library half of AC 20)."""

import shutil

import pytest

from tcw.errors import BackendError, Unreachable, UnknownProject
from tcw.work.backend import Query
from tcw.work.config import MIGRATION_GUIDE
from tcw.work.fs_backend import FsWorkBackend
from tcw.work.jira.backend import JiraBackend
from tcw.work.open import open_backend, open_project
from tests.work.projects import commit_all, connect, make_project

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


def test_a_jira_project_opens_the_jira_backend(tmp_path):
    statuses = ["inbox", "request", "spec", "plan", "implement", "review", "qa",
                "completed", "discarded"]
    p = make_project(tmp_path, "p", config={
        "backend": "jira", "jira": {
            "site": "https://x.atlassian.net", "project": "PP",
            "credentials": {"email-env": "E", "token-env": "T"},
            "fields": {"project": "TCW Project", "item": "TCW Item"}},
        "stages": {name: {"status": name.title()} for name in statuses}})
    backend = open_backend(p)
    assert isinstance(backend, JiraBackend)
    assert (backend.project, backend.jira.project) == ("p", "PP")


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
    with pytest.raises(UnknownProject, match="check the spelling"):
        open_project("nobody", p)
    shutil.rmtree(q)
    with pytest.raises(Unreachable):
        open_project("q", p)
