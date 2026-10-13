"""`work.jira` and the connected-project `jira` block (TCW-71 AC 1)."""

import copy

import pytest

from tcw.errors import BackendError
from tcw.work.jira.config import (
    JiraConfig, JiraFields, parse_delegation_block, parse_jira_config,
)
from tcw.work.open import open_backend
from tests.work.projects import make_project

MINIMAL = {"site": "https://acme.atlassian.net", "project": "TCW",
           "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_KEY"},
           "fields": {"project": "TCW Project", "item": "TCW Item"}}


def problems_of(raw):
    config, problems = parse_jira_config(raw)
    assert (config is None) == bool(problems)
    return [str(p) for p in problems]


def with_(path, value):
    raw = copy.deepcopy(MINIMAL)
    *parents, last = path
    node = raw
    for key in parents:
        node = node[key]
    if value is DELETE:
        del node[last]
    else:
        node[last] = value
    return raw


DELETE = object()


def test_a_minimal_block_parses_with_the_defaults():
    config, problems = parse_jira_config(MINIMAL)
    assert problems == []
    assert config == JiraConfig(
        site="https://acme.atlassian.net", project="TCW", email_env="TCW_JIRA_EMAIL",
        token_env="TCW_JIRA_API_KEY", fields=JiraFields("TCW Project", "TCW Item"))
    assert config.issue_type == "Task" and config.timeout == 15
    assert config.priorities == {"highest": "Highest", "high": "High",
                                 "medium": "Medium", "low": "Low", "lowest": "Lowest"}
    assert config.inbox_query is None


def test_every_key_parses():
    raw = dict(MINIMAL, **{"priorities": {"high": "Major"}, "issue-type": "Story",
                           "inbox-query": 'labels = "triage"', "timeout": 2.5})
    raw["fields"] = dict(raw["fields"], effort="Effort", complexity="Complexity")
    config, problems = parse_jira_config(raw)
    assert problems == []
    assert config.fields == JiraFields("TCW Project", "TCW Item", "Effort", "Complexity")
    assert config.priorities["high"] == "Major" and config.priorities["low"] == "Low"
    assert (config.issue_type, config.inbox_query, config.timeout) == (
        "Story", 'labels = "triage"', 2.5)


@pytest.mark.parametrize("path, value, key", [
    (("colour",), "blue", "work.jira.colour"),
    (("credentials", "password-env"), "X", "work.jira.credentials.password-env"),
    (("fields", "owner"), "Owner", "work.jira.fields.owner"),
    (("priorities", "urgent"), "Urgent", "work.jira.priorities.urgent"),
])
def test_an_unknown_key_at_any_level_is_named(path, value, key):
    raw = with_(path, value) if path[0] != "priorities" else dict(
        MINIMAL, priorities={"urgent": "Urgent"})
    assert any(p.startswith(key + ": unknown key") for p in problems_of(raw))


@pytest.mark.parametrize("path, key", [
    (("site",), "work.jira.site"),
    (("project",), "work.jira.project"),
    (("credentials",), "work.jira.credentials"),
    (("fields",), "work.jira.fields"),
    (("credentials", "token-env"), "work.jira.credentials.token-env"),
    (("fields", "item"), "work.jira.fields.item"),
])
def test_a_missing_required_key_is_named(path, key):
    assert f"{key}: required" in problems_of(with_(path, DELETE))


@pytest.mark.parametrize("path, value, key", [
    (("site",), "https://acme.atlassian.net/jira", "work.jira.site"),
    (("site",), "https://acme.atlassian.net/", "work.jira.site"),
    (("site",), "http://acme.atlassian.net", "work.jira.site"),
    (("project",), "tcw", "work.jira.project"),
    (("timeout",), 0, "work.jira.timeout"),
    (("timeout",), -1, "work.jira.timeout"),
    (("timeout",), True, "work.jira.timeout"),
    (("timeout",), float("inf"), "work.jira.timeout"),
    (("timeout",), 10 ** 400, "work.jira.timeout"),
    (("credentials", "email-env"), "TCW-JIRA-EMAIL", "work.jira.credentials.email-env"),
    (("issue-type",), "", "work.jira.issue-type"),
    (("fields", "project"), 5, "work.jira.fields.project"),
])
def test_a_bad_value_is_named(path, value, key):
    assert any(p.startswith(key + ":") for p in problems_of(with_(path, value)))


def test_not_a_mapping():
    assert problems_of("TCW") == ["work.jira: expected a mapping, got str"]


SECRET = "abc def/123-sentinel-token"


@pytest.mark.parametrize("key", ["email-env", "token-env"])
def test_a_malformed_credential_name_never_shows_its_value(key):
    problems = problems_of(with_(("credentials", key), SECRET))
    assert any(p.startswith(f"work.jira.credentials.{key}:") for p in problems)
    assert not any(SECRET in p for p in problems)


def test_no_parse_result_holds_a_credential_value(monkeypatch):
    monkeypatch.setenv("TCW_JIRA_EMAIL", SECRET)
    monkeypatch.setenv("TCW_JIRA_API_KEY", SECRET)
    config, problems = parse_jira_config(MINIMAL)
    assert SECRET not in repr(config) and not problems
    _, problems = parse_jira_config(with_(("site",), "nope"))
    assert not any(SECRET in str(p) for p in problems)


def test_open_backend_names_every_problem(tmp_path):
    p = make_project(tmp_path, "p", config={
        "backend": "jira", "jira": with_(("project",), "tcw"),
        "stages": {s: {"status": s} for s in ("inbox", "request", "spec", "plan",
                                              "implement", "review", "qa",
                                              "completed", "discarded")}})
    with pytest.raises(BackendError, match="work.jira.project"):
        open_backend(p)


# -- the connected-project `jira` block ----------------------------------------

BLOCK = {"site": "https://acme.atlassian.net", "project": "WEB", "inbox-status": "To Do",
         "credentials": {"email-env": "E", "token-env": "T"},
         "fields": {"project": "TCW Project"}}
WHERE = ("projects", "children", "web", "jira")


def test_a_delegation_block_parses():
    target, problems = parse_delegation_block(BLOCK, WHERE)
    assert problems == []
    assert (target.site, target.project, target.inbox_status, target.email_env,
            target.token_env, target.project_field) == (
        "https://acme.atlassian.net", "WEB", "To Do", "E", "T", "TCW Project")


@pytest.mark.parametrize("change, key", [
    ({"site": "https://acme.atlassian.net/x"}, "site"),
    ({"project": "web"}, "project"),
    ({"inbox-status": ""}, "inbox-status"),
    ({"credentials": {"email-env": "E", "token-env": SECRET}}, "credentials.token-env"),
    ({"fields": {"item": "TCW Item"}}, "fields.item"),
    ({"extra": 1}, "extra"),
])
def test_a_bad_delegation_block_is_named_by_key(change, key):
    target, problems = parse_delegation_block(dict(BLOCK, **change), WHERE)
    assert target is None
    text = [str(p) for p in problems]
    assert any(p.startswith(".".join(WHERE) + "." + key) for p in text), text
    assert not any(SECRET in p for p in text)


def test_a_delegation_block_missing_a_key():
    block = {k: v for k, v in BLOCK.items() if k != "inbox-status"}
    _, problems = parse_delegation_block(block, WHERE)
    assert [str(p) for p in problems] == [".".join(WHERE) + ".inbox-status: required"]
