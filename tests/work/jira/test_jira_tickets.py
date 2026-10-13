"""`tickets list`, `tickets adopt`, and the display helpers (TCW-71 AC 13, 14,
and AC 26's helper bullet)."""

import json

import pytest

from tcw.errors import NotFound, UsageError
from tcw.work.jira.mapping import text_document
from tcw.work.jira.tickets import assignable_users, ticket_link, user_name
from tests.work.jira.conftest import JiraProject, jira_config
from tests.work.jira.fake import FIELDS
from tests.work.projects import make_project

PROJECT, ITEM = FIELDS["TCW Project"], FIELDS["TCW Item"]


def raw(project, summary, status="To Do", jira_project="TCW", **custom):
    ticket = project.fake.ticket(summary, project=jira_project, status=status)
    for name, value in custom.items():
        ticket.custom[FIELDS[name.replace("_", " ")]] = value
    return ticket.key


def listed(tcw, project, *flags):
    result = tcw(["tickets", "list", *flags], project.root)
    assert result.code == 0, result.err
    return result


# -- tickets list (AC 13) -------------------------------------------------------------------


def test_the_inbox(jira_project, tcw):
    bare = raw(jira_project, "bare")
    ours = raw(jira_project, "ours", TCW_Project="tcw")
    raw(jira_project, "an item", TCW_Item="tcw/TCW-9-x")
    raw(jira_project, "theirs", TCW_Project="web")
    raw(jira_project, "at request", status="Triage")
    result = listed(tcw, jira_project)
    assert result.out.split("\n") == [bare, ours, ""]
    assert "2 tickets waiting in Jira" in result.err and "JQL: " in result.err


@pytest.fixture
def widened(tmp_path, fake):
    query = 'labels IN ("triage")'
    project = JiraProject(make_project(tmp_path, "tcw", config=jira_config(
        **{"inbox-query": query})), "tcw", fake)
    fake.add_project("WEB")
    return project


def labelled(project, summary, status="To Do", jira_project="TCW", **custom):
    key = raw(project, summary, status, jira_project, **custom)
    project.fake.tickets[key].labels.append("triage")
    return key


def test_the_inbox_query_widens_only_to_what_adopt_accepts(widened, tcw):
    plain = raw(widened, "plain")
    at_request = labelled(widened, "at request", status="Triage")
    labelled(widened, "an item", status="Triage", TCW_Item="tcw/TCW-9-x")
    labelled(widened, "theirs", status="Triage", TCW_Project="web")
    labelled(widened, "other jira project", jira_project="WEB")
    labelled(widened, "further along", status="In Progress")
    has_folder = labelled(widened, "has a folder", status="Triage")
    (widened.work / f"{has_folder}-x").mkdir(parents=True)
    result = listed(tcw, widened)
    assert result.out.split() == [plain, at_request]
    assert ') OR (labels IN ("triage"))' in result.err


def test_every_listed_key_is_adoptable(widened, tcw):
    raw(widened, "plain")
    labelled(widened, "at request", status="Triage")
    for key in listed(tcw, widened).out.split():
        result = tcw(["tickets", "adopt", key], widened.root)
        assert result.code == 0, result.err


def test_json_from_one_search(jira_project, tcw):
    described = raw(jira_project, "described")
    jira_project.fake.tickets[described].description = text_document("Do\n\nthis")
    empty = raw(jira_project, "empty")
    jira_project.fake.log.clear()
    tickets = json.loads(listed(tcw, jira_project, "--json").out)["tickets"]
    assert [t["key"] for t in tickets] == [described, empty]
    assert set(tickets[0]) == {"key", "summary", "status", "created", "reporter", "url",
                               "description"}
    assert tickets[0]["description"] == "Do\n\nthis" and tickets[1]["description"] is None
    assert tickets[0]["url"] == f"{jira_project.fake.site}/browse/{described}"
    assert len(jira_project.fake.requests("POST", "/search/jql")) == 1


def test_every_page_is_read(jira_project, tcw):
    keys = [raw(jira_project, f"t{n}") for n in range(7)]
    jira_project.fake.page_size = 3
    assert listed(tcw, jira_project).out.split() == keys


# -- tickets adopt (AC 14) -------------------------------------------------------------------


def test_adopting_from_the_inbox(jira_project, tcw):
    key = raw(jira_project, "Fix the login")
    result = tcw(["tickets", "adopt", key], jira_project.root)
    slug = f"tcw/{key}-fix-the-login"
    assert (result.code, result.out.strip()) == (0, slug)
    ticket = jira_project.fake.tickets[key]
    assert (ticket.custom[PROJECT], ticket.custom[ITEM]) == ("tcw", slug)
    assert ticket.status == "Triage"
    assert (jira_project.work / f"{key}-fix-the-login" / "item.yaml").is_file()
    edits = [b for m, p, b in jira_project.fake.log if m == "PUT"]
    assert len(edits) == 1 and set(edits[0]["fields"]) == {PROJECT, ITEM}


REFUSALS = {
    "another jira project": dict(jira_project="WEB"),
    "another tcw project": dict(TCW_Project="web"),
    "an item already": dict(TCW_Item="web/WEB-1-x"),
    "further along": dict(status="In Progress"),
    "an unmapped status": dict(status="Backlog"),
}


@pytest.mark.parametrize("case", sorted(REFUSALS) + ["a folder here", "no route"])
def test_each_refusal_writes_nothing(jira_project, tcw, case):
    jira_project.fake.add_project("WEB")
    jira_project.fake.projects["TCW"].statuses += ("Backlog",)
    key = raw(jira_project, "x", **REFUSALS.get(case, {}))
    if case == "a folder here":
        (jira_project.work / f"{key}-something").mkdir(parents=True)
    if case == "no route":
        flow = jira_project.fake.projects["TCW"]
        flow.transitions = [t for t in flow.transitions if t.to != "Triage"]
    jira_project.fake.log.clear()
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert result.code == 3, (case, result.err)
    assert jira_project.fake.writes() == []
    assert list(jira_project.work.glob(f"{key}-*")) == ([] if case != "a folder here"
                                                        else [jira_project.work / f"{key}-something"])


def test_a_missing_ticket(jira_project, tcw):
    assert tcw(["tickets", "adopt", "TCW-77"], jira_project.root).code == 4


def test_resuming_without_a_folder(jira_project, tcw):
    key = raw(jira_project, "x", TCW_Project="tcw", TCW_Item="tcw/TCW-1-exact-name")
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert (result.code, result.out.strip()) == (0, "tcw/TCW-1-exact-name")
    assert "resuming" in result.err
    assert (jira_project.work / "TCW-1-exact-name").is_dir()
    assert jira_project.fake.tickets[key].status == "Triage"


def test_resuming_with_the_folder_at_the_inbox_status(jira_project, tcw):
    key = raw(jira_project, "x", TCW_Project="tcw", TCW_Item="tcw/TCW-1-kept")
    folder = jira_project.work / "TCW-1-kept"
    folder.mkdir(parents=True)
    (folder / "item.yaml").write_text("ticket: mine\n")
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert result.code == 0, result.err
    assert jira_project.fake.tickets[key].status == "Triage"
    assert (folder / "item.yaml").read_text() == "ticket: mine\n"
    assert jira_project.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions")]


def test_finishing_a_create_that_stopped_at_its_folder(jira_project, tcw):
    flow = jira_project.fake.projects["TCW"]
    flow.statuses += ("Open",)
    flow.initial_status = "Open"
    jira_project.work.mkdir(parents=True, exist_ok=True)
    (jira_project.work / "TCW-1-half").write_text("in the way")
    assert tcw(["new", "Half"], jira_project.root).code == 1
    (jira_project.work / "TCW-1-half").unlink()
    result = tcw(["tickets", "adopt", "TCW-1"], jira_project.root)
    assert (result.code, result.out.strip()) == (0, "tcw/TCW-1-half")
    assert (jira_project.work / "TCW-1-half" / "item.yaml").is_file()
    assert jira_project.fake.tickets["TCW-1"].status == "Triage"


def test_a_ticket_naming_another_folder(jira_project, tcw):
    key = raw(jira_project, "x", TCW_Project="tcw", TCW_Item="tcw/TCW-1-named")
    (jira_project.work / "TCW-1-other").mkdir(parents=True)
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert result.code == 3 and "TCW-1-named" in result.err
    assert jira_project.fake.writes() == []


def test_filesystem_mode(tmp_path, fake, tcw):
    root = make_project(tmp_path, "p", config={})
    assert tcw(["tickets", "list"], root).code == 2
    assert tcw(["tickets", "adopt", "TCW-1"], root).code == 2
    assert fake.log == []


# -- hooks (AC 14) ---------------------------------------------------------------------------


@pytest.fixture
def hooked(tmp_path, fake):
    out = tmp_path / "post-env"
    config = jira_config()
    config["stages"]["request"]["post"] = [
        {"command": f"env | grep '^TCW_' | sort >> {out}; echo --- >> {out}"}]
    config["stages"]["request"]["pre"] = [{"command": "exit 1"}]
    project = JiraProject(make_project(tmp_path, "tcw", config=config), "tcw", fake)
    return project, out


def runs(out):
    if not out.exists():
        return []
    blocks = out.read_text().split("---\n")
    return [dict(line.split("=", 1) for line in block.splitlines()) for block in blocks
            if block.strip()]


def test_adopting_from_the_inbox_runs_post_once(hooked, tcw):
    project, out = hooked
    key = raw(project, "Hook me")
    result = tcw(["tickets", "adopt", key], project.root)
    assert result.code == 0, result.err
    env, = runs(out)
    assert (env["TCW_STAGE"], env["TCW_FROM_STAGE"]) == ("request", "inbox")
    assert env["TCW_SLUG"] == f"tcw/{key}-hook-me"


def test_adopting_at_request_has_no_from_stage(hooked, tcw):
    project, out = hooked
    key = raw(project, "Already", status="Triage")
    assert tcw(["tickets", "adopt", key], project.root).code == 0
    env, = runs(out)
    assert env["TCW_FROM_STAGE"] == ""


def test_a_failing_post_hook_keeps_the_adoption(tmp_path, fake, tcw):
    config = jira_config()
    config["stages"]["request"]["post"] = [{"command": "exit 7"}]
    project = JiraProject(make_project(tmp_path, "tcw", config=config), "tcw", fake)
    key = raw(project, "Kept")
    result = tcw(["tickets", "adopt", key], project.root)
    assert (result.code, result.out.strip()) == (6, f"tcw/{key}-kept")
    assert (project.work / f"{key}-kept").is_dir()
    assert fake.tickets[key].custom[ITEM] == f"tcw/{key}-kept"


def test_a_refused_move_runs_no_post_hook(hooked, tcw):
    project, out = hooked
    key = raw(project, "Refused")
    triage = next(t for t in project.fake.projects["TCW"].transitions if t.to == "Triage")
    project.fake.require_screen_field(triage.id, "resolution")
    assert tcw(["tickets", "adopt", key], project.root).code == 3
    assert runs(out) == []


def test_a_resumed_adoption_runs_post_once(hooked, tcw):
    project, out = hooked
    key = raw(project, "x", TCW_Project="tcw", TCW_Item="tcw/TCW-1-resumed")
    assert tcw(["tickets", "adopt", key], project.root).code == 0
    assert len(runs(out)) == 1


def test_new_runs_no_hooks(hooked, tcw):
    project, out = hooked
    assert tcw(["new", "Plain"], project.root).code == 0
    assert runs(out) == []


# -- helpers (AC 26) ---------------------------------------------------------------------------


def test_ticket_link(jira_project):
    backend = jira_project.backend()
    assert ticket_link(backend, "TCW-5-x") == ("Jira", f"{jira_project.fake.site}/browse/TCW-5")
    with pytest.raises(NotFound):
        ticket_link(backend, "2026-10-01-x")
    assert jira_project.fake.log == []


def test_user_name_from_what_was_read(jira_project):
    jira_project.fake.account("ann@example.test", "acct-ann", "Ann Lee")
    _, folder = jira_project.item("x", "x", assignee="acct-ann")
    backend = jira_project.backend()
    backend.read(folder)
    jira_project.fake.log.clear()
    assert user_name(backend, "acct-ann") == "Ann Lee"
    assert jira_project.fake.log == []
    assert user_name(backend, "acct-dev") == "Dev Eloper"
    assert len(jira_project.fake.log) == 1
    assert user_name(backend, "acct-gone") is None


def test_assignable_users(jira_project):
    jira_project.fake.account("ali@example.test", "acct-ali", "Ali Khan")
    jira_project.fake.account("bo@example.test", "acct-bo", "Bo Li")
    assert assignable_users(jira_project.backend(), "ali") == [("acct-ali", "Ali Khan")]


def test_the_helpers_are_jira_only(tmp_path, fake):
    from tcw.work.open import open_backend
    backend = open_backend(make_project(tmp_path, "p", config={}))
    for call in (lambda: ticket_link(backend, "TCW-1-x"), lambda: user_name(backend, "a"),
                 lambda: assignable_users(backend, "a")):
        with pytest.raises(UsageError):
            call()


def test_finishing_a_create_that_stopped_before_its_tcw_item(jira_project, tcw):
    jira_project.fake.projects["TCW"].statuses += ("Open",)
    key = raw(jira_project, "Half", status="Open", TCW_Project="tcw")
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert (result.code, result.out.strip()) == (0, "tcw/TCW-1-half"), result.err
    assert jira_project.fake.tickets[key].status == "Triage"


def test_a_folder_left_without_item_yaml_is_finished(jira_project, tcw):
    key = raw(jira_project, "x", status="Triage", TCW_Project="tcw",
              TCW_Item="tcw/TCW-1-kept")
    (jira_project.work / "TCW-1-kept").mkdir(parents=True)
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert (result.code, result.out.strip()) == (0, "tcw/TCW-1-kept"), result.err
    assert (jira_project.work / "TCW-1-kept" / "item.yaml").read_text() == \
        f"ticket: {jira_project.fake.site}/browse/{key}\n"


@pytest.mark.parametrize("status", ["In Progress", "Done"])
def test_a_delegated_ticket_moved_on_is_not_taken_back(jira_project, tcw, status):
    key = raw(jira_project, "x", status=status, TCW_Project="tcw")
    jira_project.fake.log.clear()
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert result.code == 3, result.err
    assert jira_project.fake.writes() == []


def test_an_item_moved_on_whose_item_yaml_is_gone_is_not_taken_back(jira_project, tcw):
    key = raw(jira_project, "x", status="In Progress", TCW_Project="tcw",
              TCW_Item="tcw/TCW-1-kept")
    (jira_project.work / "TCW-1-kept").mkdir(parents=True)
    jira_project.fake.log.clear()
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert result.code == 3 and "already the item" in result.err, result.err
    assert jira_project.fake.writes() == []
    assert not (jira_project.work / "TCW-1-kept" / "item.yaml").exists()


# -- review fix C4: a late failure still names the item (TCW-73 Design 1.8) ------------


def _read_back_fails(monkeypatch, fake):
    """Jira stops answering just as the item is read back: everything before
    it, ticket, folder and transition, has happened."""
    from tcw.work.jira.backend import JiraBackend
    real = JiraBackend.read

    def read(self, folder):
        fake.unreachable()
        return real(self, folder)
    monkeypatch.setattr(JiraBackend, "read", read)


def test_new_whose_read_back_fails_names_the_item(jira_project, tcw, monkeypatch):
    _read_back_fails(monkeypatch, jira_project.fake)
    result = tcw(["new", "Late failure"], jira_project.root)
    key = max(jira_project.fake.tickets, key=lambda k: int(k.split("-")[1]))
    slug = f"tcw/{key}-late-failure"
    assert (result.code, result.out) == (5, slug + "\n"), result
    assert f"tcw work new: created {slug}, but could not read it back" in result.err


def test_adopt_whose_read_back_fails_names_the_item(jira_project, tcw, monkeypatch):
    key = raw(jira_project, "Fix the login")
    _read_back_fails(monkeypatch, jira_project.fake)
    result = tcw(["tickets", "adopt", key], jira_project.root)
    assert (result.code, result.out) == (5, f"tcw/{key}-fix-the-login\n"), result


def test_adopt_whose_move_fails_names_the_item(jira_project, tcw, monkeypatch):
    from tcw.work.jira import client as jira
    key = raw(jira_project, "Fix the login")

    def down(*args, **kwargs):
        raise jira.TrackerUnavailable("the connection was reset")
    monkeypatch.setattr(jira_project.fake, "_transition", down)
    result = tcw(["tickets", "adopt", key], jira_project.root)
    slug = f"tcw/{key}-fix-the-login"
    assert (result.code, result.out) == (5, slug + "\n"), result
    assert (jira_project.work / f"{key}-fix-the-login" / "item.yaml").is_file()
