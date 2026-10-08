"""`create`, `update`, `comment` and `rename` in Jira mode (TCW-71 AC 5, 6, 7,
8, 15, AC 16's `comment` case, and AC 3's `edit` case)."""

import pytest

from tcw.errors import BackendError, NotFound, Refused, UsageError
from tcw.work.jira import client as jira
from tcw.work.jira.mapping import document_text
from tcw.work.model import Changes, Slug
from tests.work.jira.conftest import ME
from tests.work.jira.fake import FIELDS


def ticket_of(project, item):
    return project.fake.tickets[item.slug.folder.split("-", 2)[0] + "-"
                                + item.slug.folder.split("-", 2)[1]]


def refuse(fake, monkeypatch, method):
    def refused(*args, **kwargs):
        raise jira._for_status(400, {}, "refused by the test", "/x")
    monkeypatch.setattr(fake, method, refused)


# -- create (AC 5) ---------------------------------------------------------------------


def test_a_new_item(jira_project):
    backend = jira_project.backend()
    item = backend.create("Dark mode", Changes(add_tags=("ui",)), stage="request",
                          request="Please")
    ticket = jira_project.fake.tickets["TCW-1"]
    assert item.slug == Slug("tcw", "TCW-1-dark-mode") and item.stage == "request"
    assert ticket.custom[FIELDS["TCW Project"]] == "tcw"
    assert ticket.custom[FIELDS["TCW Item"]] == "tcw/TCW-1-dark-mode"
    assert ticket.status == "Triage" and document_text(ticket.description) == "Please"
    folder = jira_project.work / "TCW-1-dark-mode"
    assert [p.name for p in folder.iterdir()] == ["item.yaml"]
    assert (folder / "item.yaml").read_text() == \
        f"ticket: {jira_project.fake.site}/browse/TCW-1\n"


def test_no_route_to_request_leaves_a_plain_ticket(jira_project, tcw):
    project = jira_project.fake.projects["TCW"]
    project.transitions = [t for t in project.transitions if t.to != "Triage"]
    result = tcw(["new", "Stuck"], jira_project.root)
    assert result.code == 3 and result.out.strip() == "TCW-1"
    assert FIELDS["TCW Item"] not in jira_project.fake.tickets["TCW-1"].custom
    assert list(jira_project.work.glob("TCW-1-*")) == []


def test_a_ticket_created_at_the_request_status_needs_no_move(jira_project):
    jira_project.fake.projects["TCW"].initial_status = "Triage"
    jira_project.backend().create("Direct", Changes(), stage="request", request=None)
    assert not jira_project.fake.requests("POST", "/transitions")


def test_no_priority_field(jira_project, tcw):
    jira_project.fake.projects["TCW"].priority = False
    result = tcw(["new", "Prioritized", "--priority", "high"], jira_project.root)
    assert result.code == 3 and result.out == ""
    assert jira_project.fake.writes() == []
    assert tcw(["new", "Plain"], jira_project.root).code == 0
    create, = [body for method, path, body in jira_project.fake.log
               if (method, path) == ("POST", "/rest/api/3/issue")]
    assert "priority" not in create["fields"]


def test_only_the_request_stage(jira_project):
    with pytest.raises(UsageError):
        jira_project.backend().create("x", Changes(), stage="spec", request=None)
    assert jira_project.fake.log == []


def test_step_4_fails(jira_project, monkeypatch, tcw):
    refuse(jira_project.fake, monkeypatch, "_edit")
    result = tcw(["new", "Half"], jira_project.root)
    assert (result.code, result.out.strip()) == (1, "TCW-1")
    assert "tickets adopt TCW-1" in result.err
    assert not (jira_project.work / "TCW-1-half").exists()


def test_step_5_fails(jira_project, tcw):
    jira_project.work.mkdir(parents=True, exist_ok=True)
    (jira_project.work / "TCW-1-half").write_text("in the way")
    result = tcw(["new", "Half"], jira_project.root)
    assert (result.code, result.out.strip()) == (1, "TCW-1")
    assert "tickets adopt TCW-1" in result.err


def test_step_6_refused(jira_project, tcw):
    triage = next(t for t in jira_project.fake.projects["TCW"].transitions
                  if t.to == "Triage")
    jira_project.fake.require_screen_field(triage.id, "resolution")
    result = tcw(["new", "Half"], jira_project.root)
    assert (result.code, result.out.strip()) == (1, "tcw/TCW-1-half")
    assert "resolution is required" in result.err and "advance" in result.err
    assert (jira_project.work / "TCW-1-half" / "item.yaml").is_file()
    assert jira_project.fake.tickets["TCW-1"].status == "To Do"


def test_step_6_drops(jira_project, monkeypatch, tcw):
    original = jira_project.fake._transition

    def dropped(ticket, body, route):
        original(ticket, body, route)
        raise jira.TrackerUnavailable("connection lost")
    monkeypatch.setattr(jira_project.fake, "_transition", dropped)
    result = tcw(["new", "Half"], jira_project.root)
    assert (result.code, result.out.strip()) == (5, "tcw/TCW-1-half")


def test_step_7_fails(jira_project, monkeypatch, tcw):
    _, blocker = jira_project.item("Blocker", "blocker")
    refuse(jira_project.fake, monkeypatch, "_link")
    result = tcw(["new", "Half", "--blocked-by", blocker], jira_project.root)
    assert (result.code, result.out.strip()) == (1, "tcw/TCW-2-half")
    assert "not made: add TCW-1" in result.err
    assert jira_project.fake.tickets["TCW-2"].status == "Triage"


def test_a_blocker_that_is_not_a_jira_ticket_is_refused_before_any_write(jira_project):
    with pytest.raises(Refused, match="not a Jira ticket"):
        jira_project.backend().create("x", Changes(add_blocked_by=("2026-10-01-old",)),
                                      stage="request", request=None)
    assert jira_project.fake.writes() == []


# -- children (AC 6) ---------------------------------------------------------------------


def test_children_take_the_type_below_their_parent(jira_project):
    _, epic = jira_project.item("Epic", "epic", issue_type="Epic")
    _, task = jira_project.item("Task", "task")
    _, sub = jira_project.item("Sub", "sub", issue_type="Subtask")
    backend = jira_project.backend()
    under_epic = backend.create("a", Changes(parent=epic), stage="request", request=None)
    under_task = backend.create("b", Changes(parent=task), stage="request", request=None)
    assert ticket_of(jira_project, under_epic).issue_type.name == "Task"
    assert ticket_of(jira_project, under_task).issue_type.name == "Subtask"
    assert under_task.parent == Slug("tcw", task)
    writes = len(jira_project.fake.writes())
    with pytest.raises(Refused, match="Subtask"):
        backend.create("c", Changes(parent=sub), stage="request", request=None)
    assert len(jira_project.fake.writes()) == writes


def test_a_task_cannot_move_under_another_task(jira_project):
    _, one = jira_project.item("One", "one")
    _, two = jira_project.item("Two", "two")
    with pytest.raises(Refused, match="Task"):
        jira_project.backend().update(two, Changes(parent=one))
    assert jira_project.fake.writes() == []


# -- update (AC 7) ------------------------------------------------------------------------


def test_one_edit_carries_every_field(jira_project):
    _, folder = jira_project.item("Old", "x", labels=["marketing", "api"])
    item = jira_project.backend().update(folder, Changes(
        title="New", priority="low", effort="high", add_tags=("ui",),
        remove_tags=("api",)))
    assert jira_project.fake.writes() == [("PUT", "/rest/api/3/issue/TCW-1")]
    assert (item.title, item.priority, item.effort, item.tags) == ("New", "low", "high",
                                                                   ("ui",))
    assert jira_project.fake.tickets["TCW-1"].labels == ["marketing", "ui"]


def test_blockers_are_links(jira_project):
    _, blocker = jira_project.item("Blocker", "blocker")
    _, folder = jira_project.item("Blocked", "blocked")
    backend = jira_project.backend()
    item = backend.update(folder, Changes(add_blocked_by=(blocker,)))
    assert item.blocked_by == (Slug("tcw", blocker),)
    assert jira_project.fake.writes() == [("POST", "/rest/api/3/issueLink")]
    link, = jira_project.fake.links
    assert backend.read(blocker).blocked_by == ()
    item = backend.update(folder, Changes(remove_blocked_by=(blocker,)))
    assert item.blocked_by == () and jira_project.fake.links == []
    assert jira_project.fake.writes()[-1] == ("DELETE", f"/rest/api/3/issueLink/{link.id}")


def test_a_failed_link_is_named_and_a_rerun_adds_it_once(jira_project, monkeypatch):
    _, blocker = jira_project.item("Blocker", "blocker")
    _, folder = jira_project.item("Blocked", "blocked")
    backend = jira_project.backend()
    original = jira_project.fake._link
    refuse(jira_project.fake, monkeypatch, "_link")
    with pytest.raises(BackendError, match="fields were saved.*not made: add TCW-1"):
        backend.update(folder, Changes(title="T", add_blocked_by=(blocker,)))
    monkeypatch.setattr(jira_project.fake, "_link", original)
    change = Changes(title="T", add_blocked_by=(blocker,))
    jira_project.backend().update(folder, change)
    jira_project.backend().update(folder, change)
    assert len(jira_project.fake.links) == 1
    assert len(jira_project.fake.requests("POST", "/issueLink")) == 2   # refused, then one


def test_removing_a_blocker_that_is_gone_is_skipped(jira_project):
    _, blocker = jira_project.item("Blocker", "blocker")
    _, folder = jira_project.item("Blocked", "blocked")
    jira_project.backend().update(folder, Changes(remove_blocked_by=(blocker,)))
    assert jira_project.fake.writes() == []


def test_typing_a_key_to_edit(jira_project, tcw):
    key, folder = jira_project.item("Old", "x")
    result = tcw(["edit", key, "--title", "y"], jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[key].summary == "y"


# -- assignee (AC 8) ------------------------------------------------------------------------


@pytest.fixture
def people(jira_project):
    fake = jira_project.fake
    fake.account("ann@example.test", "acct-ann", "Ann Lee")
    fake.account("anna@example.test", "acct-anna", "Anna Park")
    fake.account("bob@example.test", "acct-bob", "Bob Ray")
    return jira_project


def test_one_match_is_used(people):
    _, folder = people.item("x", "x")
    assert people.backend().update(folder, Changes(assignee="bob")).assignee == "acct-bob"


def test_an_account_id_is_used_directly(people):
    _, folder = people.item("x", "x")
    assert people.backend().update(folder, Changes(assignee=ME)).assignee == ME
    assert not people.fake.requests("GET", "/user/assignable")


def test_no_match_and_several(people, tcw):
    _, folder = people.item("x", "x")
    with pytest.raises(NotFound):
        people.backend().update(folder, Changes(assignee="zed"))
    with pytest.raises(Refused, match="Ann Lee.*Anna Park"):
        people.backend().update(folder, Changes(assignee="ann"))
    assert people.fake.writes() == []
    assert tcw(["edit", folder, "--assignee", "zed"], people.root).code == 4
    assert tcw(["edit", folder, "--assignee", "ann"], people.root).code == 3


# -- comment (AC 16) and rename (AC 15) ----------------------------------------------------------


def test_comment_text_reads_back_exactly(jira_project):
    key, folder = jira_project.item("x", "x")
    text = "a [b] *c*\n\nd\ne"
    backend = jira_project.backend()
    backend.comment(folder, text)
    assert jira_project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/comment")]
    body = jira_project.fake.tickets[key].comments[0]["body"]
    assert document_text(body) == text
    assert [p["type"] for p in body["content"]] == ["paragraph", "paragraph"]
    assert [n["type"] for n in body["content"][1]["content"]].count("hardBreak") == 1
    assert backend.read_comments(folder)[0].text == text


def test_rename(jira_project):
    key, folder = jira_project.item("x", "old-words")
    (jira_project.work / "TCW-2-other").mkdir()
    (jira_project.work / "TCW-2-other" / "notes.md").write_text(f"see {folder}\n")
    item = jira_project.backend().rename(folder, "new-words")
    assert item.slug == Slug("tcw", f"{key}-new-words")
    assert jira_project.fake.custom(key, "TCW Item") == f"tcw/{key}-new-words"
    assert (jira_project.work / f"{key}-new-words").is_dir()
    assert not (jira_project.work / folder).exists()


@pytest.mark.parametrize("words", ["TCW-9-new", "Not Words", "x/y"])
def test_rename_keeps_the_key_and_takes_words(jira_project, words):
    _, folder = jira_project.item("x", "old")
    with pytest.raises(UsageError):
        jira_project.backend().rename(folder, words)
    assert jira_project.fake.writes() == []


def test_rename_with_the_key_given(jira_project):
    key, folder = jira_project.item("x", "old")
    assert jira_project.backend().rename(folder, f"{key}-new").slug.folder == f"{key}-new"


def test_a_failed_tcw_item_edit_keeps_the_folder(jira_project, monkeypatch):
    _, folder = jira_project.item("x", "old")
    refuse(jira_project.fake, monkeypatch, "_edit")
    with pytest.raises(BackendError):
        jira_project.backend().rename(folder, "new")
    assert (jira_project.work / folder).is_dir()


def test_rename_reports_other_mentions(jira_project, capsys):
    key, folder = jira_project.item("x", "old")
    note = jira_project.work / folder / "notes.md"
    note.write_text(f"{folder} is mine\n")
    jira_project.backend().rename(folder, "new")
    assert f"names {folder}, not rewritten" in capsys.readouterr().err
    assert (jira_project.work / f"{key}-new" / "notes.md").read_text() == f"{folder} is mine\n"


def test_step_6_without_permission_is_not_unreachable(jira_project, monkeypatch, tcw):
    def forbidden(ticket, body, route):
        raise jira_project.fake._error(403, route, "You do not have permission")
    monkeypatch.setattr(jira_project.fake, "_transition", forbidden)
    result = tcw(["new", "Half"], jira_project.root)
    assert (result.code, result.out.strip()) == (1, "tcw/TCW-1-half")
    assert "advance tcw/TCW-1-half --to request" in result.err
