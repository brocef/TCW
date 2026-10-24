"""Jira: a parent or blocker Jira cannot link is a recorded reference, kept in
the item's state file (TCW-114 Design 3.3; AC 7, AC 27; plan Steps 13-15).

`app` keeps its items in Jira on site A; `far` in Jira on site B; `files` in
the files backend. All three sit side by side, `far` and `files` placed in
`app`'s manifest."""

from __future__ import annotations

import json
import shutil

import pytest
import yaml

from tcw.work.jira.backend import same_site
from tests.projectfiles import write_manifest
from tests.serve.conftest import serve_project  # noqa: F401
from tests.statefiles import ITEM_STATE, read_state, write_state
from tests.work.jira.conftest import JiraProject, jira_config
from tests.work.jira.fake import FakeJira, install_sites
from tests.work.projects import make_project, write_item

SITE_B = "https://other.atlassian.net"
F = "2026-10-01-f"


@pytest.fixture
def three(tmp_path, monkeypatch, fake):
    far_fake = FakeJira(SITE_B)
    far_fake.add_project("FAR")
    install_sites(monkeypatch, fake, far_fake)
    app = make_project(tmp_path, "app", config=jira_config("app"))
    far = make_project(tmp_path, "far", config=jira_config("far", jira_project="FAR",
                                                           site=SITE_B))
    files = make_project(tmp_path, "files")
    write_item(files, F, {"title": "F", "stage": "request"})
    write_manifest(app, {"far": "../far", "files": "../files"})
    far_project = JiraProject(far, "far", far_fake, "FAR")
    far_key, far_folder = far_project.item("Far one", "far-one")
    return JiraProject(app, "app", fake), far_project, files, f"far.work/{far_folder}"


def state(root, folder):
    return read_state(root / "docs" / "work" / folder / ITEM_STATE)


def made_folder(project: JiraProject, out: str) -> str:
    return out.strip().split("/", 1)[1]


def creates(fake):
    return [b for m, p, b in fake.log if m == "POST" and p == "/rest/api/3/issue"]


def test_new_records_a_parent_and_a_blocker_jira_cannot_link(tcw, three):
    app, far, files, far_id = three
    result = tcw(["new", "x", "--parent", f"files.work/{F}", "--blocked-by", far_id],
                 app.root)
    assert result.code == 0, result.err
    [body] = creates(app.fake)
    assert "parent" not in body["fields"]
    assert not app.fake.links
    folder = made_folder(app, result.out)
    data = state(app.root, folder)
    assert set(data) == {"ticket", "parent", "blocked-by"}
    assert data["parent"] == f"files.work/{F}"
    assert data["blocked-by"] == [far_id]
    assert result.err.count("Jira shows no link for it") == 2
    assert "'s parent files.work/" in result.err and "'s blocker far.work/" in result.err
    assert "is not a ticket on https://acme.atlassian.net" in result.err


@pytest.fixture
def with_item(three):
    app, far, files, far_id = three
    key, epic = app.item("Epic", "epic", issue_type="Epic")
    key2, task = app.item("Task", "task")
    app.fake.tickets[key2].parent = key
    return app, far, files, far_id, task, epic


def test_edit_to_a_recorded_parent_clears_the_jira_parent_first(tcw, with_item):
    app, _, _, far_id, task, epic = with_item
    result = tcw(["edit", task, "--parent", far_id], app.root)
    assert result.code == 0, result.err
    assert any(b and b.get("fields", {}).get("parent") is None and "parent" in b["fields"]
               for _, _, b in app.fake.requests("PUT"))
    assert state(app.root, task)["parent"] == far_id
    assert "Jira shows no link for it" in result.err


def test_edit_to_a_ticket_on_this_site_removes_the_recorded_parent(tcw, with_item):
    app, _, _, far_id, task, epic = with_item
    assert tcw(["edit", task, "--parent", far_id], app.root).code == 0
    result = tcw(["edit", task, "--parent", f"app.work/{epic}"], app.root)
    assert result.code == 0, result.err
    assert "parent" not in state(app.root, task)
    key = task.split("-task")[0]
    assert app.fake.tickets[key].parent == epic.split("-epic")[0]


def test_parent_none_removes_both(tcw, with_item):
    app, _, _, far_id, task, _ = with_item
    assert tcw(["edit", task, "--parent", far_id], app.root).code == 0
    assert tcw(["edit", task, "--parent", ""], app.root).code == 0
    assert "parent" not in state(app.root, task)
    assert app.fake.tickets[task.split("-task")[0]].parent is None


def test_a_ticket_of_another_tcw_project_on_this_site_is_linked(tcw, three, tmp_path):
    app, _, _, _ = three
    other = make_project(tmp_path, "oth", config=jira_config("oth"))
    write_manifest(app.root, {"oth": "../oth"})
    oth = JiraProject(other, "oth", app.fake)
    key, folder = oth.item("Other epic", "epic", issue_type="Epic")
    result = tcw(["new", "y", "--parent", f"oth.work/{folder}"], app.root)
    assert result.code == 0, result.err
    assert "parent" not in state(app.root, made_folder(app, result.out))
    assert creates(app.fake)[-1]["fields"]["parent"] == {"key": key}


def test_a_parent_whose_project_is_not_here_stops_before_any_write(tcw, three):
    app, _, files, _ = three
    shutil.rmtree(files)
    result = tcw(["new", "y", "--parent", f"files.work/{F}"], app.root)
    assert result.code == 5
    assert "files" in result.err
    assert creates(app.fake) == []


def test_a_dropped_connection_after_the_clear_is_finished_by_running_again(tcw, with_item):
    app, _, _, far_id, task, _ = with_item
    before = state(app.root, task)
    app.fake.drop_after_next_write(then_unreachable=True)
    result = tcw(["edit", task, "--parent", far_id], app.root)
    assert result.code == 5
    assert state(app.root, task) == before
    app.fake.down = None
    clears = len(app.fake.requests("PUT"))
    result = tcw(["edit", task, "--parent", far_id], app.root)
    assert result.code == 0, result.err
    assert state(app.root, task)["parent"] == far_id
    # The Jira parent was already gone: no second clear.
    assert len(app.fake.requests("PUT")) == clears


def test_a_state_file_that_cannot_be_written_names_the_values_to_set_again(
        tcw, three, monkeypatch):
    app, _, _, far_id = three
    from tcw.work.jira.backend import JiraBackend

    def broken(self, folder, key, **kw):
        raise OSError("read-only file system")
    monkeypatch.setattr(JiraBackend, "_item_file", broken)
    result = tcw(["new", "x", "--parent", f"files.work/{F}"], app.root)
    assert result.code != 0
    assert "tcw work tickets adopt" in result.err
    assert f"--parent files.work/{F}" in result.err


def test_a_recorded_blocker_is_added_and_removed_with_no_link(tcw, with_item):
    app, _, _, _, task, _ = with_item
    assert tcw(["edit", task, "--blocked-by", f"files.work/{F}"], app.root).code == 0
    assert state(app.root, task)["blocked-by"] == [f"files.work/{F}"]
    assert tcw(["edit", task, "--unblocked-by", f"files.work/{F}"], app.root).code == 0
    assert "blocked-by" not in state(app.root, task)
    assert not app.fake.requests("POST", "issueLink")


@pytest.mark.parametrize("a,b,same", [
    ("https://acme.atlassian.net", "https://ACME.atlassian.net", True),
    ("https://acme.atlassian.net", "https://acme2.atlassian.net", False),
])
def test_same_site(a, b, same):
    assert same_site(a, b) is same


def test_a_site_written_in_capitals_is_this_site(tcw, three, tmp_path):
    app, _, _, _ = three
    other = make_project(tmp_path, "caps", config=jira_config(
        "caps", site="https://ACME.atlassian.net"))
    write_manifest(app.root, {"caps": "../caps"})
    caps = JiraProject(other, "caps", app.fake)
    _, folder = caps.item("Caps epic", "epic", issue_type="Epic")
    result = tcw(["new", "z", "--parent", f"caps.work/{folder}"], app.root)
    assert result.code == 0, result.err
    assert "parent" not in state(app.root, made_folder(app, result.out))


# -- reading (Step 14) -----------------------------------------------------------------


@pytest.fixture
def recorded(tcw, three):
    app, far, files, far_id = three
    result = tcw(["new", "x", "--parent", f"files.work/{F}", "--blocked-by", far_id],
                 app.root)
    assert result.code == 0, result.err
    return app, far_id, made_folder(app, result.out)


def test_show_and_list_give_the_recorded_values(tcw, recorded):
    app, far_id, folder = recorded
    shown = json.loads(tcw(["show", folder, "--json"], app.root).out)
    item = shown.get("item", shown)
    assert item["parent"] == f"files.work/{F}"
    assert far_id in item["blocked-by"]
    listed = tcw(["list", "--parent", f"files.work/{F}"], app.root)
    assert listed.code == 0, listed.err
    assert folder in listed.out


def test_list_by_a_parent_on_this_site_asks_jira(tcw, with_item):
    app, _, _, _, task, epic = with_item
    tcw(["list", "--parent", f"app.work/{epic}"], app.root)
    searches = [b["jql"] for m, p, b in app.fake.log if p.endswith("/search/jql")]
    assert any("parent" in q for q in searches)


# -- tcw validate (Step 15) ------------------------------------------------------------


def validate(monkeypatch, capsys, root):
    from tcw.cli import main
    monkeypatch.chdir(root)
    code = main(["validate"])
    out = capsys.readouterr()
    return code, out.out + out.err


def test_validate_passes_a_recorded_parent_that_is_there(recorded, monkeypatch, capsys):
    app, _, folder = recorded
    before = len(app.fake.log)
    code, out = validate(monkeypatch, capsys, app.root)
    assert f"files.work/{F}" not in out, out
    assert len(app.fake.log) == before          # offline


def test_validate_warns_of_a_recorded_parent_naming_nothing(recorded, monkeypatch, capsys):
    app, _, folder = recorded
    path = app.root / "docs" / "work" / folder / ITEM_STATE
    data = yaml.safe_load(path.read_text())
    data["parent"] = "files.work/2026-10-01-gone"
    write_state(path, yaml.safe_dump({k: v for k, v in data.items()
                                      if k != "tcw-version"}))
    _, out = validate(monkeypatch, capsys, app.root)
    assert "parent references a missing item, files.work/2026-10-01-gone" in out


def test_validate_cannot_check_a_project_not_here(recorded, monkeypatch, capsys, tmp_path):
    app, _, _ = recorded
    shutil.rmtree(tmp_path / "files")
    _, out = validate(monkeypatch, capsys, app.root)
    assert f"parent files.work/{F} is in a project that cannot be reached" in out


def test_validate_refuses_a_recorded_ticket_on_this_site(tcw, with_item, monkeypatch,
                                                          capsys):
    app, _, _, _, task, epic = with_item
    path = app.root / "docs" / "work" / task / ITEM_STATE
    data = yaml.safe_load(path.read_text())
    data["parent"] = f"app.work/{epic}"
    write_state(path, yaml.safe_dump({k: v for k, v in data.items()
                                      if k != "tcw-version"}))
    _, out = validate(monkeypatch, capsys, app.root)
    assert (f"parent app.work/{epic} is a ticket on https://acme.atlassian.net; run "
            f"tcw work edit app.work/{task} --parent app.work/{epic} to make it a Jira "
            f"link") in out


def test_a_parent_whose_jira_settings_are_undecided_stops_with_exit_7(tcw, three,
                                                                       tmp_path):
    """`inh` takes `work.jira` from `base`, which is not on this machine
    (TCW-109): which place the value belongs in cannot be told."""
    from tests.projectfiles import connect_projects
    app, _, _, _ = three
    config = jira_config("inh")
    del config["jira"]
    inh = make_project(tmp_path, "inh", config=config)
    connect_projects(inh, "parent", "base")
    write_manifest(inh, {"base": "../base"})
    write_item(inh, "INH-1-epic", "ticket: https://acme.atlassian.net/browse/INH-1\n")
    write_manifest(app.root, {"inh": "../inh"})
    before = len(app.fake.log)
    result = tcw(["new", "z", "--parent", "inh.work/INH-1-epic"], app.root)
    assert result.code == 7, result.err
    assert "'base'" in result.err and "not on this machine" in result.err
    assert len(app.fake.log) == before


def test_list_json_gives_the_recorded_values(tcw, recorded):
    app, far_id, folder = recorded
    listed = json.loads(tcw(["list", "--json"], app.root).out)
    rows = listed if isinstance(listed, list) else listed["items"]
    [row] = [r for r in rows if folder in json.dumps(r)]
    assert row["parent"] == f"files.work/{F}"
    assert row["blocked-by"] == [far_id]


def test_the_folder_check_of_a_recorded_parent_runs_offline(tcw, with_item, monkeypatch,
                                                             capsys):
    """TCW-111 Design 3.2: an item whose folder sits in another item's folder
    that its parent does not name; a recorded parent is read from the state
    file, so no `--remote` is needed."""
    app, _, _, far_id, task, epic = with_item
    assert tcw(["edit", task, "--parent", far_id], app.root).code == 0
    work = app.root / "docs" / "work"
    (work / task).rename(work / epic / task)
    before = len(app.fake.log)
    _, out = validate(monkeypatch, capsys, app.root)
    assert (f"app.work/{epic}/{task} sits in the folder of app.work/{epic}, but its "
            f"parent is {far_id}") in out, out
    assert len(app.fake.log) == before


def test_remote_validate_reports_a_jira_parent_beside_a_recorded_one(
        tcw, with_item, monkeypatch, capsys):
    app, _, _, far_id, task, epic = with_item
    path = app.root / "docs" / "work" / task / ITEM_STATE
    data = yaml.safe_load(path.read_text())
    data["parent"] = far_id
    write_state(path, yaml.safe_dump({k: v for k, v in data.items()
                                      if k != "tcw-version"}))
    from tcw.cli import main
    monkeypatch.chdir(app.root)
    main(["validate", "--remote"])
    out = capsys.readouterr()
    text = out.out + out.err
    epic_key = epic.split("-epic")[0]
    assert (f"its ticket has the Jira parent {epic_key} while its state file records "
            f"the parent {far_id}") in text, text


# -- the web routes (AC 7, the web bullet) --------------------------------------------


def test_the_web_routes_give_the_recorded_sentence_as_a_warning(three, with_item,
                                                                 serve_project):
    app, _, _, far_id, task, epic = with_item
    served = serve_project(app.root)
    answer = served.post("/api/work", {"title": "x", "properties": {
        "parent": f"files.work/{F}"}})
    assert answer.status == 201, answer.body
    [said] = [w for w in answer.json["warnings"]
              if "Jira shows no link for it" in w["message"]]
    assert said["where"] == "parent"
    # The page edits no Jira item's properties (`writable`), so the PATCH
    # half of the plan's bullet has no route to reach: it stays refused.
    answer = served.patch(f"/api/work/{task}", {"changes": {"parent": far_id},
                                                "expected": {"parent": f"app.work/{epic}"}})
    assert answer.status == 403, answer.body
