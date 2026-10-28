"""Jira mode without the TCW Project and TCW Item fields (TCW-118, the design
note `optional-jira-fields.md`): the item folders alone say which tickets are
this project's items, and no request reads or writes either field.

The fake's site has neither field (`tcw_fields = False`), so a create or edit
naming one is refused, and `no_tcw_field_named` checks the log besides."""

from __future__ import annotations

import json

import yaml

import pytest

from tcw.cli import main
from tcw.errors import BackendError
from tcw.migrate.jira import plan_tickets
from tcw.work.backend import Query
from tcw.work.model import Changes, Slug
from tests.statefiles import ITEM_STATE
from tests.work.jira.conftest import JiraProject, jira_config, key_folder
from tests.work.jira.fake import FIELDS
from tests.work.projects import make_project

PROJECT, ITEM = FIELDS["TCW Project"], FIELDS["TCW Item"]


def bare_config(**extra) -> dict:
    config = jira_config(**extra)
    config["jira"]["fields"] = {"effort": "Effort", "complexity": "Complexity"}
    return config


@pytest.fixture
def bare(tmp_path, fake) -> JiraProject:
    fake.tcw_fields = False
    return JiraProject(make_project(tmp_path, "tcw", config=bare_config()), "tcw", fake)


def item(project, summary="A ticket", words="x", *, status="Triage", **values):
    """A ticket and its folder here, with no TCW field set. `(key, folder)`."""
    ticket = project.fake.ticket(summary, project=project.jira_project, status=status,
                                 **values)
    name = f"{ticket.key}-{words}"
    key_folder(project.work, name)
    return ticket.key, name


def no_tcw_field_named(fake) -> None:
    for method, path, body in fake.log:
        text = path + json.dumps(body)
        assert PROJECT not in text and ITEM not in text, (method, path, body)


def folders(items):
    return [i.slug.folder for i in items]


def searches(fake):
    return [body["jql"] for _, _, body in fake.requests("POST", "/search/jql")]


# -- the configuration ----------------------------------------------------------------


def test_metadata_resolves_only_the_fields_configured(bare):
    ids = bare.backend().metadata().field_ids
    assert set(ids) == {"effort", "complexity"}
    assert not bare.backend().tcw_fields


def test_one_tcw_field_alone_is_refused(tmp_path, fake, tcw):
    config = bare_config()
    config["jira"]["fields"]["item"] = "TCW Item"
    root = make_project(tmp_path, "tcw", config=config)
    result = tcw(["list"], root)
    assert result.code == 1
    assert "work.jira.fields.project: required when work.jira.fields.item is given" \
        in result.err
    assert fake.log == []


# -- 1. listing --------------------------------------------------------------------------


def test_list_is_the_tickets_the_folders_name(bare, capsys):
    _, open_ = item(bare, "Open", "open", status="In Progress")
    _, done = item(bare, "Done", "done", status="Done")
    bare.fake.ticket("Not an item here", status="Triage")
    key_folder(bare.work, "TCW-99-gone")
    backend = bare.backend()
    assert folders(backend.list(Query())) == [open_]
    assert folders(backend.list(Query(all=True))) == [open_, done]
    assert folders(backend.list(Query(stages=frozenset({"completed"})))) == [done]
    query = searches(bare.fake)[0]
    assert query.startswith('project = "TCW" AND key IN (') and "TCW-99" in query
    assert 'status NOT IN ("Done", "Won\'t Do")' in query
    assert capsys.readouterr().err == ""
    no_tcw_field_named(bare.fake)


def test_list_narrows_by_label_parent_and_assignee(bare):
    parent_key, parent = item(bare, "Epic", "epic")
    _, child = item(bare, "Child", "child", parent=parent_key, labels=["ui"],
                    assignee="acct-dev")
    item(bare, "Other", "other")
    backend = bare.backend()
    assert folders(backend.list(Query(tags=frozenset({"ui"})))) == [child]
    assert folders(backend.list(Query(parent=Slug("tcw", parent)))) == [child]
    assert folders(backend.list(Query(assignee="acct-dev"))) == [child]
    assert any('labels IN ("ui")' in q for q in searches(bare.fake))
    assert any('parent = "TCW-1"' in q for q in searches(bare.fake))
    no_tcw_field_named(bare.fake)


def test_list_searches_by_chunks_and_keeps_the_creation_order(bare):
    made = [item(bare, f"Item {n}", f"i{n}")[1] for n in range(1, 102)]
    listed = folders(bare.backend().list(Query()))
    assert listed == made
    assert len(searches(bare.fake)) == 2


def test_a_refused_key_search_reads_each_key_and_filters_locally(bare):
    """Jira refuses a whole `key IN` search when one key is missing or
    hidden, so each key of the chunk is read and `query.matches` narrows."""
    _, open_ = item(bare, "Open", "open", status="In Progress", labels=["ui"])
    _, other = item(bare, "Other label", "other", status="In Progress")
    _, done = item(bare, "Done", "done", status="Done", labels=["ui"])
    key, _ = item(bare, "Hidden", "hidden", labels=["ui"])
    bare.fake.hide(key)
    key_folder(bare.work, "TCW-99-gone")
    bare.fake.refuse_missing_key_search = True
    backend = bare.backend()
    assert folders(backend.list(Query(tags=frozenset({"ui"})))) == [open_]
    assert folders(backend.list(Query(all=True))) == [open_, other, done]
    assert searches(bare.fake) and all("labels IN" in q or "key IN" in q
                                       for q in searches(bare.fake))


def test_a_ticket_answered_under_another_key_is_not_listed(bare):
    """`TCW-9` now answers as `TCW-2`, which has its own folder: it is listed
    once, under its own folder, and the stale `TCW-9` folder not at all."""
    _, kept = item(bare, "Kept", "kept")
    moved_key, moved = item(bare, "Moved", "moved")
    key_folder(bare.work, "TCW-9-stale")
    bare.fake.tickets["TCW-9"] = bare.fake.tickets[moved_key]
    backend = bare.backend()
    assert folders(backend.list(Query())) == [kept, moved]
    bare.fake.refuse_missing_key_search = True
    bare.fake.hide("TCW-77")
    key_folder(bare.work, "TCW-77-hidden")
    assert folders(backend.list(Query())) == [kept, moved]


def test_tickets_created_at_once_are_ordered_by_key(bare):
    names = [item(bare, f"Item {n}", f"i{n}")[1] for n in range(1, 4)]
    for key in ("TCW-1", "TCW-2", "TCW-3"):
        bare.fake.tickets[key].created = bare.fake.tickets["TCW-1"].created
    assert folders(bare.backend().list(Query())) == names


def test_a_parent_with_no_folder_here_is_untracked_without_a_search(bare):
    other = bare.fake.ticket("Someone else's epic")
    _, child = item(bare, "Child", "child", parent=other.key)
    found, = bare.backend().list(Query())
    assert found.parent is None and found.untracked == (other.key,)
    assert len(searches(bare.fake)) == 1


# -- 2. the inbox ---------------------------------------------------------------------------


def test_the_inbox_is_the_inbox_status_with_no_folder_here(bare, tcw):
    waiting = bare.fake.ticket("Waiting", status="To Do").key
    item(bare, "Adopted here", "here", status="To Do")
    bare.fake.ticket("At request", status="Triage")
    result = tcw(["tickets", "list"], bare.root)
    assert result.code == 0, result.err
    assert result.out.split() == [waiting]
    query, = searches(bare.fake)
    assert query == 'project = "TCW" AND status = "To Do" ORDER BY created ASC'
    no_tcw_field_named(bare.fake)


def test_the_inbox_query_offers_nothing_at_the_request_status(tmp_path, fake, tcw):
    fake.tcw_fields = False
    project = JiraProject(make_project(tmp_path, "tcw", config=bare_config(
        **{"inbox-query": 'labels IN ("triage")'})), "tcw", fake)
    labelled = [fake.ticket(s, status=status, labels=["triage"]).key
                for s, status in (("inbox", "To Do"), ("request", "Triage"))]
    result = tcw(["tickets", "list"], project.root)
    assert result.out.split() == labelled[:1]


# -- 3. adopting ---------------------------------------------------------------------------


def test_adopting_from_the_inbox_writes_only_the_move(bare, tcw):
    key = bare.fake.ticket("Fix the login", status="To Do").key
    result = tcw(["tickets", "adopt", key], bare.root)
    assert (result.code, result.out.strip()) == (0, f"tcw.work/{key}-fix-the-login"), \
        result.err
    assert bare.fake.tickets[key].status == "Triage"
    assert (bare.work / f"{key}-fix-the-login" / ITEM_STATE).is_file()
    assert bare.fake.writes() == [("POST", f"/rest/api/3/issue/{key}/transitions")]
    no_tcw_field_named(bare.fake)


def test_adopting_at_the_request_status_with_no_folder_is_refused(bare, tcw):
    key = bare.fake.ticket("Someone's item", status="Triage").key
    result = tcw(["tickets", "adopt", key], bare.root)
    assert result.code == 3
    assert "may be an item of another repository" in result.err
    assert "move it back to 'To Do'" in result.err
    assert bare.fake.writes() == [] and list(bare.work.glob(f"{key}-*")) == []


def test_an_adoption_stopped_before_the_move_is_resumed(bare, tcw, monkeypatch):
    from tcw.work.jira import client as jira
    key = bare.fake.ticket("Fix the login", status="To Do").key
    real = bare.fake._transition

    def down(*args, **kwargs):
        raise jira.TrackerUnavailable("the connection was reset")
    monkeypatch.setattr(bare.fake, "_transition", down)
    result = tcw(["tickets", "adopt", key], bare.root)
    folder = bare.work / f"{key}-fix-the-login"
    assert result.code == 5 and (folder / ITEM_STATE).is_file()
    assert bare.fake.tickets[key].status == "To Do"
    # The folder is the record of the adoption: offered no more, and resumed.
    assert tcw(["tickets", "list"], bare.root).out == ""
    monkeypatch.setattr(bare.fake, "_transition", real)
    result = tcw(["tickets", "adopt", key], bare.root)
    assert (result.code, result.out.strip()) == (0, f"tcw.work/{key}-fix-the-login"), \
        result.err
    assert "resuming" in result.err
    assert bare.fake.tickets[key].status == "Triage" and (folder / ITEM_STATE).is_file()


def test_an_adoption_stopped_after_the_move_is_finished(bare, tcw):
    key = bare.fake.ticket("Fix the login", status="Triage").key
    (bare.work / f"{key}-fix-the-login").mkdir(parents=True)
    bare.fake.log.clear()
    result = tcw(["tickets", "adopt", key], bare.root)
    assert (result.code, result.out.strip()) == (0, f"tcw.work/{key}-fix-the-login"), \
        result.err
    assert (bare.work / f"{key}-fix-the-login" / ITEM_STATE).is_file()
    assert bare.fake.writes() == []


def test_an_item_at_request_with_its_state_file_is_refused(bare, tcw):
    key, name = item(bare, "Adopted", "adopted", status="Triage")
    result = tcw(["tickets", "adopt", key], bare.root)
    assert result.code == 3
    assert f"{key} is already the item tcw.work/{name}" in result.err
    assert bare.fake.writes() == []


def test_a_bare_folder_for_a_ticket_moved_on_is_not_taken_back(bare, tcw):
    key = bare.fake.ticket("Moved on", status="In Progress").key
    (bare.work / f"{key}-moved-on").mkdir(parents=True)
    result = tcw(["tickets", "adopt", key], bare.root)
    assert result.code == 3 and bare.fake.writes() == []


# -- 4. creating ------------------------------------------------------------------------------


def test_a_new_item_sets_no_tcw_field(bare):
    created = bare.backend().create("Dark mode", Changes(add_tags=("ui",)),
                                    stage="request", request="Please")
    assert created.slug == Slug("tcw", "TCW-1-dark-mode") and created.stage == "request"
    assert bare.fake.tickets["TCW-1"].custom == {}
    assert (bare.work / "TCW-1-dark-mode" / ITEM_STATE).is_file()
    assert [m for m, p in bare.fake.writes() if m == "PUT"] == []
    no_tcw_field_named(bare.fake)


def test_a_create_stopped_at_its_folder_says_how_to_finish(bare, tcw):
    flow = bare.fake.projects["TCW"]
    flow.statuses += ("Open",)
    flow.initial_status = "Open"
    bare.work.mkdir(parents=True, exist_ok=True)
    (bare.work / "TCW-1-half").write_text("in the way")
    result = tcw(["new", "Half"], bare.root)
    assert result.code == 1
    assert "move TCW-1 to 'To Do' in Jira, then run `tcw work tickets adopt TCW-1`" \
        in result.err
    # Moved there, the ticket is adopted as any other.
    (bare.work / "TCW-1-half").unlink()
    bare.fake.tickets["TCW-1"].status = "To Do"
    result = tcw(["tickets", "adopt", "TCW-1"], bare.root)
    assert (result.code, result.out.strip()) == (0, "tcw.work/TCW-1-half"), result.err


# -- 5. moving and renaming -------------------------------------------------------------------


def test_a_rename_is_the_folder_move_alone(bare, tcw):
    key, name = item(bare, "Old", "old")
    bare.fake.log.clear()
    result = tcw(["rename", name, "new-words"], bare.root)
    assert result.code == 0, result.err
    assert (bare.work / f"{key}-new-words" / ITEM_STATE).is_file()
    assert bare.fake.writes() == []
    no_tcw_field_named(bare.fake)


def test_a_move_whose_ticket_is_gone_is_refused(bare, tcw):
    _, epic = item(bare, "Epic", "epic")
    key, name = item(bare, "Child", "child")
    bare.fake.hide(key)
    result = tcw(["move", name, "--into", epic], bare.root)
    assert result.code == 4 and f"Jira has no ticket {key}" in result.err
    assert (bare.work / name).is_dir() and bare.fake.writes() == []


def test_a_move_reads_and_writes_no_ticket(bare, tcw):
    _, epic = item(bare, "Epic", "epic")
    key, name = item(bare, "Child", "child")
    bare.fake.log.clear()
    result = tcw(["move", name, "--into", epic], bare.root)
    assert result.code == 0, result.err
    assert (bare.work / epic / name / ITEM_STATE).is_file()
    assert bare.fake.writes() == []
    no_tcw_field_named(bare.fake)


# -- 6. reading one item ------------------------------------------------------------------------


def test_show_reads_no_tcw_field(bare, tcw):
    _, name = item(bare, "Shown", "shown", description=None)
    result = tcw(["show", name], bare.root)
    assert result.code == 0, result.err
    assert "Shown" in result.out
    no_tcw_field_named(bare.fake)


# -- 7. tcw validate --remote ----------------------------------------------------------------


def remote(project, monkeypatch, capsys):
    project.fake.log.clear()
    monkeypatch.chdir(project.root)
    code = main(["validate", "--remote"])
    captured = capsys.readouterr()
    assert project.fake.writes() == []
    return code, [line for line in captured.out.splitlines() if line], captured.err


def test_validate_remote_is_clean_without_the_fields(bare, monkeypatch, capsys):
    item(bare, "Item", "x")
    bare.fake.ticket("A sub-task", issue_type="Subtask", parent="TCW-1")
    code, lines, err = remote(bare, monkeypatch, capsys)
    assert (code, lines) == (0, []), lines
    assert "1 item folders checked against their tickets" in err
    assert "the model checks ran over 1 items" in err
    no_tcw_field_named(bare.fake)


def test_validate_remote_reports_a_folder_whose_ticket_is_gone(bare, monkeypatch, capsys):
    item(bare, "Item", "x")
    key_folder(bare.work, "TCW-9-gone")
    code, lines, _ = remote(bare, monkeypatch, capsys)
    assert code == 1
    assert "error: tcw.work/TCW-9-gone: its ticket TCW-9 does not exist in Jira, or " \
           "this account cannot see it" in lines


def test_validate_remote_says_how_to_fill_fields_turned_on_later(jira_project,
                                                                monkeypatch, capsys):
    """A ticket made while the project ran without the fields, once they are
    configured: `list` leaves it out, so `validate --remote` names both values."""
    jira_project.item("Item", "x")
    key, name = item(jira_project, "Made before", "before")
    code, lines, _ = remote(jira_project, monkeypatch, capsys)
    assert code == 1
    assert (f"error: tcw.work/{name}: its ticket {key} has no TCW Project or TCW Item, "
            f"as when the project ran without the TCW fields; fill them in Jira by hand "
            f"(TCW Project 'tcw', TCW Item 'tcw.work/{name}'), or leave the fields out "
            f"of work.jira.fields, since `tcw work list` leaves the ticket out until "
            f"then") in lines


# -- 9. tcw migrate ---------------------------------------------------------------------------


def test_migrate_plans_no_ticket_edit_and_asks_jira_nothing(bare):
    item(bare, "Item", "x")
    bare.fake.log.clear()
    assert plan_tickets("tcw", bare.backend()) == ([], [], [])
    assert bare.fake.log == []


def test_migrate_plans_the_jira_half_of_a_4_0_project_without_the_fields(bare):
    from tcw.migrate.jira import half
    item(bare, "Item", "x")
    bare.fake.log.clear()
    planned = half(bare.root, "tcw")
    assert (planned.tickets, planned.reports, planned.blockers) == ([], [], [])
    assert bare.fake.log == []


def test_setting_tcw_item_values_is_refused(bare):
    with pytest.raises(BackendError, match="names no TCW Item field"):
        bare.backend().set_item_values([("TCW-1", "a", "b")])
    assert bare.fake.log == []


# -- references between repositories ---------------------------------------------------------


@pytest.fixture
def pair(tmp_path, fake):
    """`app` with the TCW fields and `web` without, in one Jira project on one
    site, each placed in the other's manifest."""
    from tests.projectfiles import write_manifest
    app = JiraProject(make_project(tmp_path, "app", config=jira_config("app")), "app", fake)
    web = JiraProject(make_project(tmp_path, "web", config=bare_config()), "web", fake)
    write_manifest(app.root, {"web": "../web"})
    write_manifest(web.root, {"app": "../app"})
    _, app_item = app.item("App one", "app-one")
    _, web_item = item(web, "Web one", "web-one")
    return app, web, f"app.work/{app_item}", f"web.work/{web_item}"


@pytest.mark.parametrize("side", ["with", "without"])
def test_a_reference_to_the_other_project_is_recorded(pair, tcw, side):
    app, web, app_id, web_id = pair
    here, there = (app, web_id) if side == "with" else (web, app_id)
    result = tcw(["new", "x", "--blocked-by", there], here.root)
    assert result.code == 0, result.err
    assert not here.fake.links
    folder = result.out.strip().split("/", 1)[1]
    assert yaml.safe_load((here.work / folder / ITEM_STATE).read_text())[
        "blocked-by"] == [there]
    assert "a link to another project's ticket needs the TCW fields in both " \
           "projects, so it is recorded" in result.err
    # Offline validate does not advise making it a Jira link.
    result = tcw_validate(here.root)
    assert "to make it a Jira link" not in result


def test_a_reference_within_the_project_is_still_a_link(bare, tcw):
    _, blocker = item(bare, "Blocker", "blocker")
    result = tcw(["new", "x", "--blocked-by", blocker], bare.root)
    assert result.code == 0, result.err
    assert len(bare.fake.links) == 1
    found, = [i for i in bare.backend().list(Query()) if i.title == "x"]
    assert found.blocked_by == (Slug("tcw", blocker),)


def tcw_validate(root) -> str:
    import io
    import contextlib
    import os
    out = io.StringIO()
    cwd = os.getcwd()
    os.chdir(root)
    try:
        with contextlib.redirect_stdout(out):
            main(["validate"])
    finally:
        os.chdir(cwd)
    return out.getvalue()
