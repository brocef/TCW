"""TCW-113 Design 3.5 (plan Step 7): a Jira search is made once per command
for each search key, and a write drops what was kept. AC 28."""

from __future__ import annotations

import os

import pytest

import tcw.work.jira.client as jira_client
from tcw.config import begin_command, command_span, command_state, end_command
from tcw.work.jira.backend import _kept_search
from tests.families import build_family, item_folder, jira_mode
from tests.work.jira.fake import FakeJira

EMAIL, TOKEN = "TCW_TEST_JIRA_EMAIL", "TCW_TEST_JIRA_TOKEN"


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv(EMAIL, "dev@example.test")
    monkeypatch.setenv(TOKEN, "token")
    fake = FakeJira().install(monkeypatch)
    fake.account("dev@example.test", "a-1", "Ann")
    return fake


@pytest.fixture
def signed_in(fake, monkeypatch):
    """The email each request to the fake was sent with, in order."""
    sent = []
    answer = jira_client.JiraClient._request

    def request(client, method, path, body=None, *, timeout=None):
        sent.append((method, path, body, os.environ.get(client.config.email_env)))
        return answer(client, method, path, body, timeout=timeout)
    monkeypatch.setattr(jira_client.JiraClient, "_request", request)
    return sent


@pytest.fixture
def family(tmp_path, fake):
    family = build_family(tmp_path, docs_passes="none")
    family.renamed = {}
    for pid in ("shared", "desktop", "server", "other"):
        family.renamed[pid] = jira_mode(family, pid, fake)[item_folder(pid)]
    return family


def item_searches(sent, project: str | None = None) -> list:
    """The item searches sent (never a key search), with the email each was
    sent with."""
    return [(body, email) for method, path, body, email in sent
            if method == "POST" and path.endswith("/search/jql")
            and "key in" not in body["jql"].lower()
            and (project is None or f'project = "{project}"' in body["jql"])]


# -- AC 28 -----------------------------------------------------------------------------


def test_ac28_one_search_for_projects_that_share_one(family, signed_in):
    ran = family.run("shared", "work", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    assert len(item_searches(signed_in, "APP")) == 1
    assert len(item_searches(signed_in)) == 1
    for pid in ("shared", "desktop", "server"):
        own = family.run(pid, "work", "list")
        assert own.code == 0, own.err
        assert [line for line in ran.lines if line.startswith(f"{pid}.work/")] == own.lines
    assert not [line for line in ran.lines if line.startswith("other.")]
    assert ran.lines == [f"{pid}.work/{family.renamed[pid]}"
                         for pid in ("shared", "desktop", "server")]


def test_ac28_a_second_jira_project_is_its_own_search(family, fake, signed_in):
    document = family.config("desktop")
    document["work"]["jira"]["project"] = "DESK"
    fake.add_project("DESK")
    family.write_config("desktop", document)
    ran = family.run("shared", "work", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    assert len(item_searches(signed_in, "APP")) == 1
    assert len(item_searches(signed_in, "DESK")) == 1


def test_ac28_another_account_is_its_own_search(family, fake, signed_in, monkeypatch):
    monkeypatch.setenv("DESK_EMAIL", "bea@example.test")
    fake.account("bea@example.test", "b-1", "Bea")
    document = family.config("desktop")
    document["work"]["jira"]["credentials"]["email-env"] = "DESK_EMAIL"
    family.write_config("desktop", document)
    ran = family.run("shared", "work", "list", "--scope", "down")
    assert ran.code == 0, ran.err
    made = item_searches(signed_in, "APP")
    assert [email for _, email in made] == ["dev@example.test", "bea@example.test"]


def test_ac28_a_second_command_makes_its_own_search(family, signed_in):
    assert family.run("shared", "work", "list", "--scope", "down").code == 0
    assert family.run("shared", "work", "list", "--scope", "down").code == 0
    assert len(item_searches(signed_in, "APP")) == 2


# -- `_kept_search` ----------------------------------------------------------------------


class Client:
    def __init__(self, site="https://a.example", email_env="E", token_env="T"):
        self.config = type("C", (), {"site": site, "email_env": email_env,
                                     "token_env": token_env})()
        self.calls = []

    account_key = jira_client.JiraClient.account_key

    def search(self, text, fields):
        self.calls.append((text, tuple(fields)))
        return [{"key": "APP-1", "fields": {"f": [1]}}]


class Backend:
    def __init__(self, client):
        self.client = client


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("E", "dev@example.test")
    monkeypatch.setenv("T", "secret-token")


def test_kept_once_and_answered_as_a_copy(credentials):
    client = Client()
    with command_span():
        first = _kept_search(Backend(client), "q", ["f"])
        second = _kept_search(Backend(client), "q", ["f"])
    assert client.calls == [("q", ("f",))]
    assert first == second and first is not second
    assert first[0]["fields"]["f"] is not second[0]["fields"]["f"]


@pytest.mark.parametrize("change", ["site", "email", "token", "text", "fields"])
def test_each_part_of_the_key_makes_its_own_search(credentials, monkeypatch, change):
    client = Client()
    with command_span():
        _kept_search(Backend(client), "q", ["f"])
        text, fields = "q", ["f"]
        if change == "site":
            client.config.site = "https://b.example"
        elif change == "email":
            monkeypatch.setenv("E", "bea@example.test")
        elif change == "token":
            monkeypatch.setenv("T", "another-token")
        elif change == "text":
            text = "q2"
        else:
            fields = ["f", "g"]
        _kept_search(Backend(client), text, fields)
    assert len(client.calls) == 2


def test_outside_a_command_nothing_is_kept(credentials):
    client = Client()
    assert command_state() is None
    _kept_search(Backend(client), "q", ["f"])
    _kept_search(Backend(client), "q", ["f"])
    assert len(client.calls) == 2


def test_the_key_holds_a_digest_never_the_token(credentials, monkeypatch):
    client = Client()
    with command_span() as state:
        _kept_search(Backend(client), "q", ["f"])
        [key] = state[jira_client.KEPT_SEARCHES]
        assert "secret-token" not in repr(key)
        digest = key[2]
        assert len(digest) == 64 and set(digest) <= set("0123456789abcdef")
        monkeypatch.setenv("T", "  secret-token \n")
        monkeypatch.setenv("E", " dev@example.test ")
        _kept_search(Backend(client), "q", ["f"])
    assert len(client.calls) == 1


# -- a write drops what was kept (plan choice 16) -------------------------------------


WRITES = {
    "create_issue": lambda c, key: c.create_issue({"project": {"key": "APP"},
                                                   "summary": "x",
                                                   "issuetype": {"id": "10001"}}),
    "edit_issue": lambda c, key: c.edit_issue(key, fields={"summary": "y"}),
    "apply_transition": lambda c, key: c.apply_transition(key, "999"),
    "add_comment": lambda c, key: c.add_comment(key, {"type": "doc", "version": 1,
                                                      "content": []}),
    "add_link": lambda c, key: c.add_link("Blocks", key, key),
    "delete_link": lambda c, key: c.delete_link("1"),
}


@pytest.mark.parametrize("write", sorted(WRITES))
def test_each_write_drops_the_kept_searches(fake, write):
    fake.add_project("APP")
    ticket = fake.ticket("t", project="APP")
    client = jira_client.JiraClient(_config(fake))
    backend = Backend(client)
    text = 'project = "APP"'
    with command_span():
        _kept_search(backend, text, ["summary"])
        try:
            WRITES[write](client, ticket.key)
        except jira_client.TrackerError:
            pass        # a refused write still drops them, before sending
        _kept_search(backend, text, ["summary"])
    made = [b for m, p, b in fake.requests("POST", "/search/jql") if b["jql"] == text]
    assert len(made) == 2


def _config(fake):
    return type("C", (), {"site": fake.site, "email_env": EMAIL, "token_env": TOKEN,
                          "timeout": 5})()


def test_a_write_outside_a_command_raises_nothing(fake):
    fake.add_project("APP")
    ticket = fake.ticket("t", project="APP")
    assert command_state() is None
    jira_client.JiraClient(_config(fake)).edit_issue(ticket.key, fields={"summary": "y"})


def test_begin_and_end_command_hold_the_state():
    assert command_state() is None
    begin_command()
    try:
        assert command_state() == {}
    finally:
        end_command()
    assert command_state() is None
