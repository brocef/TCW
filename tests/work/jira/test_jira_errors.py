"""Design 10's table: each client error becomes one `tcw/errors.py` class and
its exit code, here through `read` (TCW-71 AC 20)."""

import pytest

from tcw.errors import BackendError, NotFound, Unreachable
from tcw.work.jira import client as jira
from tests.work.jira.conftest import TOKEN_ENV, jira_config
from tests.work.projects import make_project


def status(code, headers=None):
    return lambda fake: setattr(fake, "down", jira._for_status(code, headers or {},
                                                               "", "/x"))


ROWS = [
    ("unreachable", lambda f: f.unreachable(), Unreachable, 5),
    ("5xx", status(503), Unreachable, 5),
    ("429", lambda f: f.rate_limited("30"), Unreachable, 5),
    ("401", lambda f: f.unauthorized(), BackendError, 1),
    ("403", status(403), BackendError, 1),
    ("404", status(404), NotFound, 4),
    ("400", status(400), BackendError, 1),
]


@pytest.mark.parametrize("name, switch, error, code", ROWS, ids=[r[0] for r in ROWS])
def test_each_row(jira_project, tcw, name, switch, error, code):
    _, folder = jira_project.item("A", "a")
    switch(jira_project.fake)
    with pytest.raises(error):
        jira_project.backend().read(folder)
    result = tcw(["show", folder], jira_project.root)
    assert result.code == code, result.err


def test_a_rate_limit_names_retry_after_and_is_not_retried(jira_project):
    _, folder = jira_project.item("A", "a")
    jira_project.fake.rate_limited("30")
    jira_project.fake.log.clear()
    with pytest.raises(Unreachable, match="Retry after 30s"):
        jira_project.backend().read(folder)
    assert len(jira_project.fake.log) == 1


def test_an_unset_credential_names_the_variable(jira_project, monkeypatch, tcw):
    _, folder = jira_project.item("A", "a")
    monkeypatch.delenv(TOKEN_ENV)
    with pytest.raises(BackendError, match=TOKEN_ENV):
        jira_project.backend().read(folder)
    assert tcw(["show", folder], jira_project.root).code == 1
    assert jira_project.fake.log == []


def test_an_answer_of_the_wrong_shape(jira_project, monkeypatch, tcw):
    _, folder = jira_project.item("A", "a")
    monkeypatch.setattr(jira_project.fake, "_issue",
                        lambda *a, **k: {"key": "TCW-1", "fields": []})
    with pytest.raises(BackendError, match="unexpected shape"):
        jira_project.backend().read(folder)
    assert tcw(["show", folder], jira_project.root).code == 1


def test_a_missing_site_is_named_as_the_site(jira_project, tcw):
    """A host with no Jira answers 404 to every request; the first one is to an
    endpoint every site has, so the message names `work.jira.site` and the
    exit is 1, not "not found" (4)."""
    jira_project.fake.site_missing = True
    result = tcw(["list"], jira_project.root)
    assert result.code == 1, result.err
    assert "check that work.jira.site" in result.err
    assert "no such resource" not in result.err


def test_a_missing_ticket_is_still_not_found(jira_project, tcw):
    _, folder = jira_project.item("A", "a")
    jira_project.fake.tickets.clear()
    result = tcw(["show", folder], jira_project.root)
    assert result.code == 4, result.err


def test_a_missing_project_on_a_real_site_is_still_not_found(tmp_path, fake, tcw):
    """`/myself` answers, so the project's own 404 stands."""
    root = make_project(tmp_path, "tcw", config=jira_config(jira_project="NOPE"))
    result = tcw(["list"], root)
    assert result.code == 4, result.err
    assert "work.jira.site" not in result.err
