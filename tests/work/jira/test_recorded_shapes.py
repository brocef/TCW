"""The fake answers in the shapes a real Jira site does (TCW-71 AC 24, Design
15.2).

`recorded/` holds one answer per endpoint and status, captured from `TCWTEST`
by the live check (`capture.py`). For each endpoint the backend reads, this
test lists the key paths it reads, and asserts that every one present in the
recorded answer is present, at the same nesting, in the fake's answer to the
same request. So the fake cannot invent a shape Jira does not send. It also
asserts that no recorded file names a person or the real site.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tcw.work.jira.mapping import text_document
from tests.work.jira.fake import FIELDS, SITE

RECORDED = Path(__file__).parent / "recorded"
FILES = sorted(RECORDED.glob("*.json"))
REAL_HOST = "proposit.atlassian.net"

#: Configured custom fields, by role, as `{role}` in a path.
ROLES = {"project": "TCW Project", "item": "TCW Item", "effort": "Effort",
         "complexity": "Complexity"}

_ISSUE = ["key", "fields.summary", "fields.status.name", "fields.created",
          "fields.priority.name", "fields.labels", "fields.assignee.accountId",
          "fields.assignee.displayName", "fields.parent.key",
          "fields.issuelinks.*.id", "fields.issuelinks.*.type.name",
          "fields.issuelinks.*.inwardIssue.key", "fields.issuetype.name",
          "fields.description", "fields.{project}", "fields.{item}",
          "fields.{effort}.value", "fields.{complexity}.value"]

#: What the backend reads from each endpoint's answer, by recorded file. `*`
#: is any element of a list. Writes are absent: their answers are read only as
#: success or failure (client.py), and so are the error bodies.
READS = {
    "get-myself-200.json": ["accountId"],
    "get-user-200.json": ["accountId", "displayName"],
    "get-issue-key-200.json": _ISSUE,
    # A search never asks for the description; `read_request` reads it directly.
    "post-search-jql-200.json": ["isLast"] + [f"issues.*.{p}" for p in _ISSUE
                                              if p != "fields.description"],
    "get-issue-key-transitions-200.json": [
        "transitions.*.id", "transitions.*.name", "transitions.*.to.name",
        "transitions.*.to.id", "transitions.*.hasScreen"],
    "get-issue-key-comment-200.json": [
        "total", "comments.*.created", "comments.*.body",
        "comments.*.author.accountId", "comments.*.author.displayName"],
    "get-project-project-200.json": [
        "id", "issueTypes.*.id", "issueTypes.*.name", "issueTypes.*.hierarchyLevel",
        "issueTypes.*.subtask"],
    "get-project-project-statuses-200.json": ["*.name", "*.statuses.*.name"],
    "get-issue-createmeta-project-issuetypes-id-200.json": [
        "total", "fields.*.fieldId", "fields.*.name", "fields.*.schema.type",
        "fields.*.allowedValues.*.value"],
    "get-issue-key-editmeta-200.json": [
        "fields.summary", "fields.labels", "fields.assignee", "fields.parent",
        "fields.priority", "fields.{project}", "fields.{item}", "fields.{effort}",
        "fields.{complexity}"],
    "get-issuelinktype-200.json": ["issueLinkTypes.*.name"],
    "post-workflows-200.json": [
        "workflows.*.transitions.*.type", "workflows.*.transitions.*.toStatusReference",
        "workflows.*.transitions.*.links", "statuses.*.statusReference",
        "statuses.*.name"],
    "post-issue-201.json": ["key"],
}

#: Paths the backend reads only when a value is set, so a recorded answer may
#: lack them; every other listed path must be in the recording too, which
#: checks the lists above against what Jira really sent.
WHEN_SET = {"fields.issuelinks.*.inwardIssue.key", "fields.parent.key",
            "issues.*.fields.issuelinks.*.inwardIssue.key",
            "issues.*.fields.parent.key", "fields.{effort}.value",
            "fields.{complexity}.value", "issues.*.fields.{effort}.value",
            "issues.*.fields.{complexity}.value", "fields.description",
            "fields.assignee.accountId",
            "fields.assignee.displayName", "issues.*.fields.assignee.accountId",
            "issues.*.fields.assignee.displayName", "fields.issuelinks.*.id",
            "fields.issuelinks.*.type.name", "issues.*.fields.issuelinks.*.id",
            "issues.*.fields.issuelinks.*.type.name", "fields.*.allowedValues.*.value",
            "comments.*.author.accountId", "comments.*.author.displayName",
            "comments.*.created", "comments.*.body"}


def has(value, path: list[str]) -> bool:
    if not path:
        return True
    head, rest = path[0], path[1:]
    if head == "*":
        return isinstance(value, list) and any(has(v, rest) for v in value)
    return isinstance(value, dict) and head in value and has(value[head], rest)


def resolve(path: str, ids: dict[str, str]) -> list[str]:
    for role, field_id in ids.items():
        path = path.replace("{" + role + "}", field_id)
    return path.split(".")


def load(name: str) -> dict:
    return json.loads((RECORDED / name).read_text(encoding="utf-8"))


def recorded_ids() -> dict[str, str]:
    """The live site's ids for the configured fields, from its create screen."""
    fields = load("get-issue-createmeta-project-issuetypes-id-200.json")["response"]["fields"]
    by_name = {f["name"]: f["fieldId"] for f in fields}
    return {role: by_name[name] for role, name in ROLES.items()}


def test_every_file_is_recorded_and_read():
    names = {f.name for f in FILES}
    assert set(READS) <= names, f"not recorded: {sorted(set(READS) - names)}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_person_or_real_site_is_recorded(path):
    text = path.read_text(encoding="utf-8")
    assert "@" not in text
    assert REAL_HOST not in text
    # Avatar URLs identify a person: Gravatar's hashes an email address.
    assert "gravatar" not in text and "avatar-management" not in text


@pytest.mark.parametrize("name", sorted(READS))
def test_each_read_path_is_in_the_recording(name):
    ids = recorded_ids()
    response = load(name)["response"]
    missing = [p for p in READS[name]
               if p not in WHEN_SET and not has(response, resolve(p, ids))]
    assert not missing, f"{name}: Jira's answer has no {missing}"


@pytest.fixture
def world(jira_project):
    """Enough state that every read path has a value: an epic; a child of it
    with every property set, a comment, and a blocker."""
    fake, client = jira_project.fake, jira_project.backend().client
    epic, _ = jira_project.item("An epic", "e", issue_type="Epic")
    key, _ = jira_project.item("A child", "c", parent=epic, assignee="acct-dev",
                               labels=["ui"], priority="High",
                               description=text_document("Please."))
    fake.tickets[key].custom[FIELDS["Effort"]] = {"value": "high"}
    fake.tickets[key].custom[FIELDS["Complexity"]] = {"value": "low"}
    blocker, _ = jira_project.item("A blocker", "b")
    client.add_link("Blocks", blocker, key)
    client.add_comment(key, text_document("A comment."))
    return jira_project, client, key


def fake_request(name: str, key: str, project) -> tuple[str, str, dict | None]:
    kind = project.fake.projects["TCW"].type_by("Task")
    fields = ["summary", "status", "created", "priority", "labels", "assignee",
              "parent", "issuelinks", "issuetype", "description", *FIELDS.values()]
    return {
        "get-myself-200.json": ("GET", "/rest/api/3/myself", None),
        "get-user-200.json": ("GET", "/rest/api/3/user?accountId=acct-dev", None),
        "get-issue-key-200.json": ("GET", f"/rest/api/3/issue/{key}", None),
        "post-search-jql-200.json": ("POST", "/rest/api/3/search/jql", {
            "jql": f'key IN ("{key}")', "fields": fields, "maxResults": 100}),
        "get-issue-key-transitions-200.json": (
            "GET", f"/rest/api/3/issue/{key}/transitions?expand=transitions.fields", None),
        "get-issue-key-comment-200.json": (
            "GET", f"/rest/api/3/issue/{key}/comment?orderBy=-created&startAt=0"
                   f"&maxResults=100", None),
        "get-project-project-200.json": ("GET", "/rest/api/3/project/TCW", None),
        "get-project-project-statuses-200.json": (
            "GET", "/rest/api/3/project/TCW/statuses", None),
        "get-issue-createmeta-project-issuetypes-id-200.json": (
            "GET", f"/rest/api/3/issue/createmeta/TCW/issuetypes/{kind.id}"
                   f"?startAt=0&maxResults=100", None),
        "get-issue-key-editmeta-200.json": (
            "GET", f"/rest/api/3/issue/{key}/editmeta", None),
        "get-issuelinktype-200.json": ("GET", "/rest/api/3/issueLinkType", None),
        "post-workflows-200.json": ("POST", "/rest/api/3/workflows", {
            "projectAndIssueTypes": [{"projectId": project.fake.projects["TCW"].id,
                                      "issueTypeId": kind.id}]}),
        "post-issue-201.json": ("POST", "/rest/api/3/issue", {"fields": {
            "project": {"key": "TCW"}, "issuetype": {"id": kind.id},
            "summary": "Made by the shape test"}}),
    }[name]


@pytest.mark.parametrize("name", sorted(READS))
def test_the_fake_answers_in_jiras_shape(world, name):
    project, client, key = world
    recorded, ids = load(name)["response"], recorded_ids()
    fake_ids = {role: FIELDS[field] for role, field in ROLES.items()}
    method, path, body = fake_request(name, key, project)
    answer = client._payload(method, path, body)
    missing = [p for p in READS[name]
               if has(recorded, resolve(p, ids)) and not has(answer, resolve(p, fake_ids))]
    assert not missing, f"{name}: Jira sends {missing}, which the fake's answer lacks"


def test_the_fake_site_stands_in_for_the_real_one():
    assert SITE.endswith(".atlassian.net") and REAL_HOST not in SITE
