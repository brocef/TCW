"""The fake Jira's switches each do something (TCW-71 plan Task 6), so a later
test relying on one is not relying on a switch that does nothing."""

import pytest

from tcw.work.jira import client as jira
from tcw.work.jira import jql
from tcw.work.jira.mapping import text_document
from tests.work.jira.fake import FIELDS, SITE, FakeJira


class _Config:
    site = SITE
    email_env = "TCW_FAKE_EMAIL"
    token_env = "TCW_FAKE_TOKEN"
    timeout = 5


ITEM = FIELDS["TCW Item"]


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("TCW_FAKE_EMAIL", "ann@example.test")
    monkeypatch.setenv("TCW_FAKE_TOKEN", "t")
    fake = FakeJira().install(monkeypatch)
    fake.account("ann@example.test", "acct-ann", "Ann")
    return fake


@pytest.fixture
def client(fake):
    return jira.JiraClient(_Config())


def create(client, summary="T", issue_type="10002", **fields):
    return client.create_issue({"project": {"key": "TCW"}, "issuetype": {"id": issue_type},
                                "summary": summary, **fields})["key"]


# -- the endpoints -----------------------------------------------------------------


def test_create_read_edit_and_labels(client, fake):
    key = create(client, labels=["a"], **{ITEM: "tcw/x"})
    client.edit_issue(key, {"summary": "U"}, {"labels": [{"add": "b"}, {"remove": "a"}]})
    fields = client.issue(key)["fields"]
    assert (fields["summary"], fields["labels"], fields[ITEM]) == ("U", ["b"], "tcw/x")
    assert fields["priority"] == {"name": "Medium"}
    assert fake.writes() == [("POST", "/rest/api/3/issue"),
                             ("PUT", f"/rest/api/3/issue/{key}")]


def test_comments_page_newest_first(client, fake):
    key = create(client)
    for n in range(150):
        client.add_comment(key, text_document(f"c{n}"))
    fake.page_size = 50
    found = client.comments(key, 150)
    assert len(found) == 150 and found[0].author_id == "acct-ann"
    assert len(fake.requests("GET", "/comment")) == 2


def test_links_read_back_on_both_tickets(client, fake):
    a, b = create(client, "a"), create(client, "b")
    client.add_link("Blocks", a, b)
    on_a = client.issue(a)["fields"]["issuelinks"]
    on_b = client.issue(b)["fields"]["issuelinks"]
    assert on_a[0]["outwardIssue"]["key"] == b and on_b[0]["inwardIssue"]["key"] == a
    client.delete_link(on_a[0]["id"])
    assert client.issue(a)["fields"]["issuelinks"] == []


def test_transitions_and_a_screen_field(client, fake):
    key = create(client)
    planning = next(t for t in client.transitions(key) if t.to_status == "Planning")
    assert planning.fields == ()
    fake.require_screen_field(planning.id, "resolution")
    planning = next(t for t in client.transitions(key) if t.to_status == "Planning")
    assert planning.required == ("resolution",)
    with pytest.raises(jira.TrackerRequestInvalid, match="resolution is required"):
        client.apply_transition(key, planning.id)
    assert client.issue(key)["fields"]["status"]["name"] == "To Do"


def test_a_transition_with_a_comment_and_the_refusal_switch(client, fake):
    key = create(client)
    planning = next(t for t in client.transitions(key) if t.to_status == "Planning")
    assert planning.has_screen and planning.fields == ()
    client.apply_transition(key, planning.id, text_document("why"))
    assert client.issue(key)["fields"]["status"]["name"] == "Planning"
    assert len(client.comments(key, 5)) == 1
    # As Jira does: a comment sent with a transition that has no screen is
    # accepted and discarded.
    target = next(t for t in client.transitions(key) if t.to_status == "Triage")
    assert not target.has_screen
    client.apply_transition(key, target.id, text_document("lost"))
    assert client.issue(key)["fields"]["status"]["name"] == "Triage"
    assert len(client.comments(key, 5)) == 1
    fake.refuse_commented_transitions = True
    back = next(t for t in client.transitions(key) if t.to_status == "To Do")
    with pytest.raises(jira.TrackerRequestInvalid):
        client.apply_transition(key, back.id, text_document("again"))
    client.apply_transition(key, back.id)


def test_project_statuses_metadata_users_and_link_types(client, fake):
    project = client.project("TCW")
    assert {t["name"]: t["hierarchyLevel"] for t in project["issueTypes"]} == {
        "Epic": 1, "Task": 0, "Bug": 0, "Subtask": -1}
    assert "In QA" in [s["name"] for s in client.project_statuses("TCW")[0]["statuses"]]
    names = [f["name"] for f in client.create_metadata("TCW", "10002")]
    assert "Priority" in names and "TCW Item" in names
    assert client.myself()["accountId"] == "acct-ann"
    assert client.user("acct-ann")["displayName"] == "Ann"
    assert [u["accountId"] for u in client.assignable_users("TCW", "an", 5)] == ["acct-ann"]
    assert "Blocks" in [t["name"] for t in client.link_types()]
    flow = client.workflows(project["id"], "10002")
    assert {s["name"] for s in flow["statuses"]} >= {"Triage", "Done"}


def test_search_pages_by_token(client, fake):
    for n in range(5):
        create(client, f"t{n}", **{ITEM: f"tcw/{n}"})
    fake.page_size = 2
    found = client.search(jql.item_query("TCW", ITEM), ["summary"])
    assert [i["fields"]["summary"] for i in found] == [f"t{n}" for n in range(5)]
    assert len(fake.requests("POST", "/search/jql")) == 3


def test_the_hierarchy_is_enforced(client, fake):
    epic = create(client, "e", "10001")
    task = create(client, "t", parent={"key": epic})
    create(client, "s", "10004", parent={"key": task})
    with pytest.raises(jira.TrackerRequestInvalid, match="hierarchy"):
        create(client, "bad", "10004", parent={"key": epic})
    with pytest.raises(jira.TrackerRequestInvalid, match="parent"):
        create(client, "orphan", "10004")


def test_an_estimate_must_be_an_option(client, fake):
    key = create(client)
    with pytest.raises(jira.TrackerRequestInvalid):
        client.edit_issue(key, {FIELDS["Effort"]: {"value": "huge"}})
    client.edit_issue(key, {FIELDS["Effort"]: {"value": "very-high"}})


# -- the switches ------------------------------------------------------------------


def test_workflows_forbidden(client, fake):
    fake.workflows_forbidden = True
    with pytest.raises(jira.TrackerPermissionError):
        client.workflows(client.project("TCW")["id"], "10002")


def test_drop_after_the_next_write_applies_it(client, fake):
    key = create(client)
    fake.drop_after_next_write()
    with pytest.raises(jira.TrackerUnavailable, match="lost"):
        client.edit_issue(key, {"summary": "landed"})
    assert client.issue(key)["fields"]["summary"] == "landed"
    client.edit_issue(key, {"summary": "again"})               # only the next one


def test_drop_after_a_write_and_stay_down(client, fake):
    key = create(client)
    fake.drop_after_next_write(then_unreachable=True)
    with pytest.raises(jira.TrackerUnavailable):
        client.edit_issue(key, {"summary": "landed"})
    with pytest.raises(jira.TrackerUnavailable):
        client.issue(key)
    assert fake.tickets[key].summary == "landed"


def test_drop_before_the_next_write_does_not_apply_it(client, fake):
    key = create(client)
    fake.drop_before_next_write()
    with pytest.raises(jira.TrackerUnavailable):
        client.edit_issue(key, {"summary": "lost"})
    assert client.issue(key)["fields"]["summary"] == "T"
    client.edit_issue(key, {"summary": "again"})
    assert fake.tickets[key].summary == "again"


def test_a_missing_key_search(client, fake):
    key = create(client)
    assert client.search(jql.keys_query([key, "TCW-99"]), []) != []
    fake.refuse_missing_key_search = True
    with pytest.raises(jira.TrackerRequestInvalid):
        client.search(jql.keys_query([key, "TCW-99"]), [])
    assert len(client.search(jql.keys_query([key]), [])) == 1


def test_search_lag_hides_recent_writes_from_searches_only(client, fake):
    fake.search_lag = 3
    key = create(client, **{ITEM: "tcw/x"})
    assert client.search(jql.item_query("TCW", ITEM), []) == []
    assert client.issue(key)["key"] == key
    client.myself()
    client.myself()
    assert [i["key"] for i in client.search(jql.item_query("TCW", ITEM), [])] == [key]


def test_a_field_off_the_edit_screen(client, fake):
    key = create(client)
    fake.off_edit_screen.add(("Task", FIELDS["Effort"]))
    assert FIELDS["Effort"] not in client.edit_metadata(key)
    with pytest.raises(jira.TrackerRequestInvalid, match="not on the appropriate screen"):
        client.edit_issue(key, {FIELDS["Effort"]: {"value": "low"}})


def test_priority_off_the_create_screen(client, fake):
    fake.projects["TCW"].priority = False
    assert "Priority" not in [f["name"] for f in client.create_metadata("TCW", "10002")]
    with pytest.raises(jira.TrackerRequestInvalid):
        create(client, priority={"name": "High"})
    assert client.issue(create(client))["fields"]["priority"] is None


@pytest.mark.parametrize("switch, error", [
    (lambda f: f.unreachable(), jira.TrackerUnavailable),
    (lambda f: f.unauthorized(), jira.TrackerAuthError),
    (lambda f: f.rate_limited("30"), jira.TrackerRateLimited),
])
def test_every_request_fails(client, fake, switch, error):
    switch(fake)
    with pytest.raises(error) as raised:
        client.myself()
    if error is jira.TrackerRateLimited:
        assert raised.value.retry_after == "30"


def test_unset_credentials_are_refused_as_the_client_would(client, fake, monkeypatch):
    monkeypatch.delenv("TCW_FAKE_TOKEN")
    with pytest.raises(jira.TrackerAuthError, match="TCW_FAKE_TOKEN"):
        client.myself()
    assert fake.log == []


def test_an_unknown_site_is_unreachable(fake, monkeypatch):
    class Elsewhere(_Config):
        site = "https://other.atlassian.net"
    with pytest.raises(jira.TrackerUnavailable):
        jira.JiraClient(Elsewhere()).myself()


def test_two_accounts_by_email_variable(client, fake, monkeypatch):
    class Bob(_Config):
        email_env = "TCW_FAKE_BOB"
    monkeypatch.setenv("TCW_FAKE_BOB", "bob@example.test")
    fake.account("bob@example.test", "acct-bob", "Bob")
    assert jira.JiraClient(Bob()).myself()["accountId"] == "acct-bob"
    assert client.myself()["accountId"] == "acct-ann"
