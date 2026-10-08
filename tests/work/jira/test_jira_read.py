"""`lookup`, `read`, and the three reads (TCW-71 AC 3, 4, and the reads of 26).

The `edit` and `advance` halves of AC 3's key-typing case need writes; they
are in `test_jira_write.py` and `test_jira_advance.py`.
"""

from datetime import date, datetime, timezone

import pytest

from tcw.errors import BackendError, NotFound
from tcw.work.backend import Query
from tcw.work.jira.backend import JiraBackend
from tcw.work.jira.mapping import block_link, text_document
from tcw.work.model import Slug
from tests.work.jira.conftest import EMAIL_ENV, ME, TOKEN_ENV
from tests.work.jira.fake import FIELDS, Link
from tests.work.projects import make_project

def blocks(fake, blocker, blocked):
    fake.link_counter += 1
    fake.links.append(Link(str(fake.link_counter), "Blocks", *block_link(blocker, blocked)))


# -- lookup ------------------------------------------------------------------------


@pytest.fixture
def folders(jira_project):
    for name in ("TCW-67-x", "TCW-5-a", "2026-10-01-x"):
        (jira_project.work / name).mkdir(parents=True)
    return jira_project


def test_lookup(folders):
    backend = folders.backend()
    assert backend.lookup("tcw-67") == "TCW-67-x"
    assert backend.lookup("TCW-67") == "TCW-67-x"
    assert backend.lookup("TCW-6") is None
    assert backend.lookup("2026-10-01-x") is None
    assert backend.lookup("TCW-67-x") is None
    assert folders.fake.log == []


def test_two_folders_with_one_key(folders, tcw):
    (folders.work / "TCW-5-b").mkdir()
    with pytest.raises(BackendError, match="TCW-5-a, TCW-5-b"):
        folders.backend().lookup("TCW-5")
    assert tcw(["show", "TCW-5"], folders.root).code == 1
    assert folders.fake.log == []


def test_a_typed_key_names_the_item(jira_project, tcw):
    key, folder = jira_project.item("Typed", "x")
    result = tcw(["show", key], jira_project.root)
    assert result.code == 0, result.err
    assert f"slug: tcw/{folder}" in result.out
    assert jira_project.fake.requests("GET", f"/rest/api/3/issue/{key}")


def test_a_key_with_no_folder_is_not_found(jira_project, tcw):
    jira_project.item("Typed", "x")                       # TCW-1
    result = tcw(["show", "TCW-6"], jira_project.root)
    assert result.code == 4
    assert jira_project.fake.log == []


def test_in_filesystem_mode_a_key_is_just_a_folder_name(tmp_path, fake, tcw):
    root = make_project(tmp_path, "p", config={})
    assert tcw(["show", "TCW-67"], root).code == 4
    assert fake.log == []


# -- read --------------------------------------------------------------------------


def test_every_property_is_mapped(jira_project):
    fake = jira_project.fake
    fake.add_project("WEB")
    epic = fake.ticket("Web epic", project="WEB", issue_type="Epic")
    epic.custom[FIELDS["TCW Item"]] = "web/WEB-1-epic"
    _, blocker_folder = jira_project.item("Blocker", "blocker", status="Done")
    stray = fake.ticket("No item")
    key, folder = jira_project.item(
        "Dark mode", "dark-mode", status="Specifying", priority="High",
        labels=["ui", "marketing", "api"], assignee=ME, parent=epic.key,
        custom={FIELDS["Effort"]: {"value": "very-high"},
                FIELDS["Complexity"]: {"value": "low"}})
    blocks(fake, "TCW-1", key)
    blocks(fake, stray.key, key)
    item = jira_project.backend().read(folder)
    assert item.slug == Slug("tcw", folder)
    assert (item.title, item.stage, item.priority) == ("Dark mode", "spec", "high")
    assert (item.effort, item.complexity) == ("very-high", "low")
    assert item.tags == ("ui", "api")                        # `marketing` is ignored
    assert item.assignee == ME
    assert item.parent == Slug("web", "WEB-1-epic")
    assert item.blocked_by == (Slug("tcw", blocker_folder),)
    assert item.untracked == (stray.key,)
    assert item.created == date(2026, 10, 1)


def test_unmapped_values_read_as_none(jira_project):
    _, folder = jira_project.item("Odd", "odd", status="Backlog", priority="Blocker")
    jira_project.fake.projects["TCW"].statuses += ("Backlog",)
    item = jira_project.backend().read(folder)
    assert (item.stage, item.priority) == (None, None)


def test_a_disabled_stage_has_no_status_to_match(tmp_path, fake):
    from tests.work.jira.conftest import JiraProject, jira_config
    config = jira_config()
    config["stages"]["spec"] = {"enabled": False}
    project = JiraProject(make_project(tmp_path, "tcw", config=config), "tcw", fake)
    _, folder = project.item("x", "x", status="Specifying")
    assert project.backend().read(folder).stage is None


def test_an_untracked_parent_and_untracked_order(jira_project):
    fake = jira_project.fake
    epic = fake.ticket("Plain epic", issue_type="Epic")
    first, second = fake.ticket("b1"), fake.ticket("b2")
    key, folder = jira_project.item("Child", "child", parent=epic.key)
    blocks(fake, second.key, key)
    blocks(fake, first.key, key)
    blocks(fake, epic.key, key)
    item = jira_project.backend().read(folder)
    assert item.parent is None and item.blocked_by == ()
    assert item.untracked == (epic.key, second.key, first.key)


def test_a_missing_ticket_is_not_found(jira_project, tcw):
    (jira_project.work / "TCW-40-gone").mkdir(parents=True)
    with pytest.raises(NotFound, match="no ticket TCW-40"):
        jira_project.backend().read("TCW-40-gone")
    assert tcw(["show", "TCW-40-gone"], jira_project.root).code == 4


@pytest.mark.parametrize("folder", ["TCW-1", "nope", "TCW-1-x/../y", "2026-10-01-x"])
def test_a_folder_that_is_not_a_key_folder_here_is_not_found(jira_project, folder):
    with pytest.raises(NotFound):
        jira_project.backend().read(folder)
    assert jira_project.fake.log == []


def test_a_ticket_answered_under_another_key_is_returned_with_a_warning(
        jira_project, capsys):
    fake = jira_project.fake
    moved = fake.ticket("Moved")
    (jira_project.work / "TCW-9-moved").mkdir(parents=True)
    fake.tickets["TCW-9"] = moved
    item = jira_project.backend().read("TCW-9-moved")
    assert item.title == "Moved"
    err = capsys.readouterr().err
    assert "TCW-9" in err and moved.key in err


# -- the three reads ---------------------------------------------------------------


def test_read_request(jira_project):
    _, with_text = jira_project.item("A", "a", description=text_document("Do\n\nthis"))
    _, without = jira_project.item("B", "b")
    _, empty = jira_project.item("C", "c", description=text_document(""))
    backend = jira_project.backend()
    assert backend.read_request(with_text) == "Do\n\nthis"
    assert backend.read_request(without) is None
    assert backend.read_request(empty) is None


def test_read_comments(jira_project):
    key, folder = jira_project.item("A", "a")
    backend = jira_project.backend()
    for n in range(5):
        backend.client.add_comment(key, text_document(f"note {n}"))
    found = backend.read_comments(folder, 3)
    assert [c.text for c in found] == ["note 4", "note 3", "note 2"]
    assert {c.author for c in found} == {ME}
    assert all(c.at.tzinfo == timezone.utc for c in found)
    assert found[0].at > found[1].at


def test_read_comments_across_pages(jira_project):
    key, folder = jira_project.item("A", "a")
    ticket = jira_project.fake.tickets[key]
    for n in range(150):
        ticket.comments.append({"id": str(n), "author": None,
                                "created": f"2026-10-01T{n // 60:02d}:{n % 60:02d}:00.000+0200",
                                "body": text_document(str(n))})
    found = jira_project.backend().read_comments(folder)
    assert len(found) == 150 and found[0].text == "149" and found[0].author is None
    assert found[0].at == datetime(2026, 10, 1, 0, 29, tzinfo=timezone.utc)


def test_current_user(jira_project):
    mine, _ = jira_project.item("Mine", "mine", assignee=ME)
    jira_project.item("Theirs", "theirs", assignee="acct-other")
    backend = jira_project.backend()
    me = backend.current_user()
    assert me == ME
    found = backend.list(Query(assignee=me))
    assert [i.slug.folder for i in found] == [f"{mine}-mine"]
    assert found[0].assignee == backend.current_user()
    assert len(jira_project.fake.requests("GET", "/myself")) == 1


@pytest.mark.parametrize("variable", [EMAIL_ENV, TOKEN_ENV])
def test_no_identity_without_a_request(jira_project, monkeypatch, variable):
    monkeypatch.delenv(variable)
    assert jira_project.backend().current_user() is None
    assert jira_project.fake.log == []


@pytest.mark.parametrize("switch, cause", [
    (lambda f: f.unauthorized(), "rejected the credentials"),
    (lambda f: f.unreachable(), "could not be reached"),
])
def test_current_user_never_raises(jira_project, capsys, switch, cause):
    switch(jira_project.fake)
    assert jira_project.backend().current_user() is None
    err = capsys.readouterr().err
    assert cause in err and len(err.strip().splitlines()) == 1


def test_the_backend_declares_its_facts(jira_project):
    backend = jira_project.backend()
    assert isinstance(backend, JiraBackend)
    assert backend.external_stages == {"request", "qa"}
    assert backend.inbox_items is False
