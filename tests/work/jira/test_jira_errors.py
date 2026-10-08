"""Design 10's table: each client error becomes one `tcw/errors.py` class and
its exit code, here through `read` (TCW-71 AC 20)."""

import pytest

from tcw.errors import BackendError, NotFound, Unreachable
from tcw.work.jira import client as jira
from tests.work.jira.conftest import TOKEN_ENV


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
