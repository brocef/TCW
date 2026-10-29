"""`work.jira` and the connected-project `jira` block (TCW-71 AC 1)."""

import copy

import pytest

from tcw.errors import BackendError
from tcw.work.jira.config import (
    JiraConfig, JiraFields, parse_jira_config,
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
    (("credentials", "token-env"), "work.jira.credentials.token-env"),
])
def test_a_missing_required_key_is_named(path, key):
    assert f"{key}: required" in problems_of(with_(path, DELETE))


@pytest.mark.parametrize("given, missing", [("project", "item"), ("item", "project")])
def test_one_tcw_field_alone_names_the_other(given, missing):
    raw = with_(("fields", missing), DELETE)
    assert problems_of(raw) == [
        f"work.jira.fields.{missing}: required when work.jira.fields.{given} is "
        f"given: the two TCW fields are given together or not at all"]


def test_the_tcw_fields_are_optional_together():
    config, problems = parse_jira_config(with_(("fields",), DELETE))
    assert problems == [] and config.fields == JiraFields() and not config.fields.tcw
    config, problems = parse_jira_config(with_(("fields",), {"effort": "Effort"}))
    assert problems == [] and config.fields == JiraFields(effort="Effort")
    assert not config.fields.tcw
    assert parse_jira_config(MINIMAL)[0].fields.tcw


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


def test_every_bad_credential_name_is_named():
    raw = with_(("credentials", "email-env"), "not a name")
    raw["credentials"]["token-env"] = "also bad"
    problems = problems_of(raw)
    assert sum(p.startswith("work.jira.credentials.email-env:") for p in problems) == 1
    assert sum(p.startswith("work.jira.credentials.token-env:") for p in problems) == 1
