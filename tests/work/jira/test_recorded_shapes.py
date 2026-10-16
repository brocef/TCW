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
from tests.work.jira.capture import PROFILE, Recorder
from tests.work.jira.fake import FIELDS, SITE, Transition

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
#: is any element of a list, `?` any value of a mapping. Writes are absent: their answers are read only as
#: success or failure (client.py), and so are the error bodies.
READS = {
    "get-myself-200.json": ["accountId", "displayName"],
    "get-user-200.json": ["accountId", "displayName"],
    "get-issue-key-200.json": _ISSUE,
    # A search never asks for the description; `read_request` reads it directly.
    "post-search-jql-200.json": ["isLast"] + [f"issues.*.{p}" for p in _ISSUE
                                              if p != "fields.description"],
    "get-issue-key-transitions-200.json": [
        "transitions.*.id", "transitions.*.name", "transitions.*.to.name",
        "transitions.*.to.id", "transitions.*.hasScreen", "transitions.*.fields"],
    "get-issue-key-comment-200.json": [
        "total", "comments.*.created", "comments.*.body",
        "comments.*.author.accountId", "comments.*.author.displayName"],
    "get-project-project-200.json": [
        "id", "issueTypes.*.id", "issueTypes.*.name", "issueTypes.*.hierarchyLevel",
        "issueTypes.*.subtask"],
    "get-project-project-statuses-200.json": ["*.name", "*.statuses.*.name"],
    "get-issue-createmeta-project-issuetypes-id-200.json": [
        "total", "fields.*.fieldId", "fields.*.key", "fields.*.name",
        "fields.*.schema.type", "fields.*.allowedValues.*.value",
        "fields.*.allowedValues.*.name"],
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
    # Recorded by `test_jira_live_shapes.py` (J2), each in a file of its own: a
    # search past one page, a transition offered from one status only, and a
    # transition screen that lists a field.
    "post-search-jql-200-first-page.json": ["nextPageToken", "isLast"],
    "post-search-jql-200-next-page.json": ["isLast", "issues.*.key"],
    "post-workflows-200-directed.json": [
        "workflows.*.transitions.*.type", "workflows.*.transitions.*.toStatusReference",
        "workflows.*.transitions.*.links.*.fromStatusReference",
        "statuses.*.statusReference", "statuses.*.name"],
    "get-issue-key-transitions-200-screen-fields.json": [
        "transitions.*.id", "transitions.*.name", "transitions.*.to.name",
        "transitions.*.hasScreen", "transitions.*.fields.?.required"],
}

#: What the backend sends in a request, by recorded file, compared with what
#: the client sends the fake for the same call.
SENDS = {"post-search-jql-200-next-page.json": ["jql", "fields", "maxResults",
                                                "nextPageToken"]}

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
    if head == "?":
        return isinstance(value, dict) and any(has(v, rest) for v in value.values())
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


#: More tickets than one search page holds, for the paged search.
PAGED = 101


@pytest.fixture
def world(jira_project):
    """Enough state that every read path has a value: an epic; a child of it
    with every property set, a comment, and a blocker; a ticket at `Won't Do`
    offered a transition from there only, whose screen lists a field, as
    TCWTEST's `J2 probe: reopen` is; and more tickets than a search page holds."""
    fake, client = jira_project.fake, jira_project.backend().client
    fake.projects["TCW"].transitions.append(Transition(
        "2", "J2 probe: reopen", "To Do", sources=("Won't Do",),
        screen={"labels": False}, has_screen=True))
    fake.ticket("Closed", status="Won't Do")
    for number in range(PAGED):
        fake.ticket(f"Paged {number:03d}")
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


def _closed(project) -> str:
    return next(k for k, t in project.fake.tickets.items() if t.status == "Won't Do")


def fake_request(name: str, key: str, project) -> tuple[str, str, dict | None]:
    kind = project.fake.projects["TCW"].type_by("Task")
    fields = ["summary", "status", "created", "priority", "labels", "assignee",
              "parent", "issuelinks", "issuetype", "description", *FIELDS.values()]
    paged = {"jql": 'project = "TCW"', "fields": fields, "maxResults": 100}
    if name == "post-search-jql-200-next-page.json":
        first = project.backend().client._payload("POST", "/rest/api/3/search/jql", paged)
        paged = {**paged, "nextPageToken": first["nextPageToken"]}
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
        "post-search-jql-200-first-page.json": ("POST", "/rest/api/3/search/jql", paged),
        "post-search-jql-200-next-page.json": ("POST", "/rest/api/3/search/jql", paged),
        "post-workflows-200-directed.json": ("POST", "/rest/api/3/workflows", {
            "projectAndIssueTypes": [{"projectId": project.fake.projects["TCW"].id,
                                      "issueTypeId": kind.id}]}),
        "get-issue-key-transitions-200-screen-fields.json": (
            "GET", f"/rest/api/3/issue/{_closed(project)}/transitions"
                   f"?expand=transitions.fields", None),
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


@pytest.mark.parametrize("name", sorted(SENDS))
def test_the_client_asks_as_jira_was_asked(world, name):
    """A search past one page: the client's next-page request carries what the
    recorded one did, the token included."""
    project, client, _key = world
    recorded = load(name)["request"]
    assert not [p for p in SENDS[name] if not has(recorded, p.split("."))]
    # A client that stopped sending the token would be answered page one
    # forever, so a time limit turns that hang into a failure.
    import signal

    def _stuck(*_args):
        raise AssertionError("the client kept asking for pages: is it sending the token?")
    previous = signal.signal(signal.SIGALRM, _stuck)
    signal.alarm(20)
    try:
        client.search('project = "TCW"', ["summary"])
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    pages = [b for _m, _p, b in project.fake.requests("POST", "/search/jql")]
    assert len(pages) >= 2, "the fake answered every ticket in one page"
    missing = [p for p in SENDS[name] if not has(pages[1], p.split("."))]
    assert not missing, f"{name}: Jira was sent {missing}, which the client's request lacks"


def _profile_values(value, key: str) -> list:
    if isinstance(value, dict):
        return [v for k, v in value.items() if k == key] + \
            [x for v in value.values() for x in _profile_values(v, key)]
    if isinstance(value, list):
        return [x for v in value for x in _profile_values(v, key)]
    return []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_real_time_zone_or_locale_is_recorded(path):
    """A user object's `timeZone` and `locale` say where its person is, so the
    recordings hold only the fixed values `capture.PROFILE` writes."""
    entry = json.loads(path.read_text(encoding="utf-8"))
    for key, fixed in PROFILE.items():
        assert set(_profile_values(entry, key)) <= {fixed}, (path.name, key)


def test_the_recorder_replaces_time_zone_and_locale(tmp_path):
    recorder = Recorder(tmp_path, SITE)
    body = {"accountId": "abc", "timeZone": "Europe/Oslo", "locale": "nb_NO",
            "author": {"timeZone": "Asia/Tokyo", "locale": "ja_JP"}}
    recorder.record("GET", f"{SITE}/rest/api/3/myself", None, 200,
                    json.dumps(body).encode())
    written = json.loads((tmp_path / "get-myself-200.json").read_text())["response"]
    for user in (written, written["author"]):
        assert (user["timeZone"], user["locale"]) == ("Etc/UTC", "en_US")


def test_a_named_call_is_recorded_apart_from_the_shared_file(tmp_path):
    """Inside `named`, an answer with fewer key paths than the shared file's is
    still written, to its own file, and the shared file is left alone."""
    recorder = Recorder(tmp_path, SITE)
    url = f"{SITE}/rest/api/3/search/jql"
    rich = {"isLast": True, "issues": [{"key": "TCW-1", "fields": {"summary": "s"}}]}
    recorder.record("POST", url, None, 200, json.dumps(rich).encode())
    shared = (tmp_path / "post-search-jql-200.json").read_text()
    with recorder.named("first-page"):
        recorder.record("POST", url, b'{"jql": "x"}', 200,
                        json.dumps({"issues": [], "nextPageToken": "t"}).encode())
    named = json.loads((tmp_path / "post-search-jql-200-first-page.json").read_text())
    assert named["response"] == {"issues": [], "nextPageToken": "t"}
    assert (tmp_path / "post-search-jql-200.json").read_text() == shared
    recorder.record("POST", url, None, 200, b'{"issues": []}')
    assert (tmp_path / "post-search-jql-200.json").read_text() == shared
    # The label is cleared on leaving `named`, so a richer answer reaches the
    # shared file again; also when the block ends in an error.
    with pytest.raises(RuntimeError), recorder.named("broken"):
        raise RuntimeError
    richer = {**rich, "nextPageToken": "u"}
    recorder.record("POST", url, None, 200, json.dumps(richer).encode())
    assert json.loads((tmp_path / "post-search-jql-200.json").read_text())["response"] \
        == richer


def test_the_fake_site_stands_in_for_the_real_one():
    assert SITE.endswith(".atlassian.net") and REAL_HOST not in SITE
