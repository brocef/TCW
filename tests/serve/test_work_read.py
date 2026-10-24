"""The work API's reads: the project, the board and one item, in filesystem
mode and in the Jira-mode fixture (TCW-77 criteria 6, 8, 10 and 13, the read
parts)."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from tcw.errors import BackendError, NotFound, Unreachable
from tcw.work.model import STAGES
from tests.serve.conftest import fs_project
from tests.serve.memory import ME, NAMES, SITE
from tests.work.projects import commit_all, connect, make_project, write_item
from tests.statefiles import write_state, ITEM_STATE

STAGE_NAMES = {s.name for s in STAGES}


def ok(answer) -> Any:
    assert answer.status == 200, answer.body
    return answer.json


def keys_at_every_depth(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            found.add(key)
            found |= keys_at_every_depth(inner)
    elif isinstance(value, list):
        for inner in value:
            found |= keys_at_every_depth(inner)
    return found


def new(tcw, root, title, *flags, request="") -> str:
    made = tcw(["work", "new", title, *flags], root, stdin=request)
    assert made.code == 0, made.err
    return made.out.strip().split("/", 1)[1]


@pytest.fixture
def tagged(tmp_path, personal_on, serve_project, tcw):
    """Items tagged a, b, both and neither."""
    root = fs_project(tmp_path, tags=("a", "b"))
    folders = {
        "a": new(tcw, root, "Only a", "--tag", "a"),
        "b": new(tcw, root, "Only b", "--tag", "b"),
        "ab": new(tcw, root, "Both", "--tag", "a", "--tag", "b"),
        "none": new(tcw, root, "Neither"),
    }
    return serve_project(root), folders


# -- the project -------------------------------------------------------------------------


def test_the_project_describes_itself(fs):
    project = ok(fs.get("/api/project"))
    assert project["id"] == "p"
    assert project["recordOwner"] == "local"
    assert project["user"] == "ann"
    assert project["people"] == {}
    assert [s["name"] for s in project["stages"]] == [s.name for s in STAGES]
    assert project["tags"] == ["ui", "api"]
    assert project["scales"]["priority"][0] == "highest"
    assert project["createFields"] == ["priority", "effort", "complexity"]
    assert project["inboxItems"] is True
    assert project["axes"] == {"taxonomy": False, "capabilities": False, "work": True}
    assert "projects" not in project


def test_with_no_user_name_the_user_is_null(tmp_path, personal_on, serve_project):
    served = serve_project(fs_project(tmp_path, user=None))
    assert ok(served.get("/api/project"))["user"] is None


def test_a_disabled_stage_is_not_in_the_table(tmp_path, personal_on, serve_project):
    root = fs_project(tmp_path, config={"stages": {"plan": {"enabled": False}}})
    names = [s["name"] for s in ok(serve_project(root).get("/api/project"))["stages"]]
    assert "plan" not in names and "spec" in names


# -- the board -----------------------------------------------------------------------------


def test_the_board_is_the_clis_list(tagged, tcw):
    served, folders = tagged
    board = ok(served.get("/api/work"))
    assert board["fallback"] is False and board["people"] == {}
    listed = tcw(["work", "list", "--json"], served.root).json["items"]
    assert board["items"] == listed
    assert {i["full-id"].split("/")[1] for i in board["items"]} == set(folders.values())


def test_the_tags_filter_is_the_clis_tag_query(tagged, tcw):
    served, folders = tagged
    board = ok(served.get("/api/work?tag=a&tag=b"))
    assert {i["full-id"].split("/")[1] for i in board["items"]} == \
        {folders["a"], folders["b"], folders["ab"]}
    listed = tcw(["work", "list", "--tag", "a", "--tag", "b", "--json"],
                 served.root).json["items"]
    assert board["items"] == listed


@pytest.mark.parametrize("tag", ["!!", "-"])
def test_a_name_that_is_not_a_tag_is_a_usage_error(tagged, jira, tag):
    for served in (tagged[0], jira.served):
        answer = served.get(f"/api/work?tag={tag}")
        assert answer.status == 400, answer.body
        assert answer.json["code"] == "usage" and repr(tag) in answer.json["error"]


def test_finished_items_show_only_with_all(tagged, tcw):
    served, folders = tagged
    item = served.root / "docs" / "work" / folders["none"] / ITEM_STATE
    data = yaml.safe_load(item.read_text())
    data["stage"] = "completed"
    write_state(item, yaml.safe_dump(data))
    default = {i["full-id"] for i in ok(served.get("/api/work"))["items"]}
    every = ok(served.get("/api/work?all=1"))["items"]
    assert f"p.work/{folders['none']}" not in default
    assert f"p.work/{folders['none']}" in {i["full-id"] for i in every}
    assert every == tcw(["work", "list", "--all", "--json"], served.root).json["items"]


def test_an_unreadable_item_fails_the_board_naming_it(fs):
    write_item(fs.root, "2026-01-01-broken", "title: [unclosed\n")
    answer = fs.get("/api/work")
    assert answer.status == 500 and answer.json["code"] == "error"
    assert "2026-01-01-broken" in answer.json["error"]
    assert "Traceback" not in answer.text


def test_a_child_projects_items_are_not_on_the_board(tmp_path, personal_on,
                                                     serve_project, tcw):
    root = fs_project(tmp_path)
    child = make_project(tmp_path / "inner", "kid")
    connect(root, child, "children")
    connect(child, root, "parent")
    commit_all(child)
    mine = new(tcw, root, "Mine")
    new(tcw, child, "Theirs")
    board = ok(serve_project(root).get("/api/work"))
    assert [i["full-id"] for i in board["items"]] == [f"p.work/{mine}"]


# -- one item ---------------------------------------------------------------------------------


def test_the_item_is_the_clis_record(tagged, tcw):
    served, folders = tagged
    folder = folders["ab"]
    found = ok(served.get(f"/api/work/{folder}"))
    shown = tcw(["work", "show", folder, "--json"], served.root).json
    assert found["item"] == shown["item"]
    assert found["folder"] == folder
    assert "requestText" not in found
    assert found["link"] is None and found["people"] == {}
    assert found["warnings"] == []
    assert not keys_at_every_depth(found) & STAGE_NAMES, keys_at_every_depth(found)


def test_the_files_are_a_tab_per_enabled_stage_with_files(tmp_path, personal_on,
                                                          serve_project, tcw):
    root = fs_project(tmp_path, config={"stages": {"plan": {"enabled": False}}})
    folder = new(tcw, root, "Thing", request="please\n")
    found = ok(serve_project(root).get(f"/api/work/{folder}"))
    tabs = [f["stage"] for f in found["files"] if f["stage"]]
    expected = [s.name for s in STAGES
                if s.artifact != "none" and s.name != "plan"]
    assert tabs == expected
    first = found["files"][0]
    assert first["document"]["present"] is True
    assert first["document"]["path"] == f"{tabs[0]}/{tabs[0]}.md"
    assert found["files"][-1]["artifact"] == "declaration"
    assert {v["stage"] for v in found["verdicts"]} == {"review", "qa"}
    assert {v["verdict"] for v in found["verdicts"]} == {"none"}


def test_comments_are_oldest_first(fs, tcw):
    folder = new(tcw, fs.root, "Talked about")
    for text in ("one", "two"):
        assert tcw(["work", "comment", folder], fs.root, stdin=text).code == 0
    found = ok(fs.get(f"/api/work/{folder}"))
    assert [c["text"].strip() for c in found["comments"]] == ["one", "two"]
    assert found["commentsLimited"] is False


def test_an_unknown_folder_is_404(fs):
    answer = fs.get("/api/work/2026-01-01-nothing")
    assert answer.status == 404 and answer.json["code"] == "not-found"


@pytest.mark.parametrize("name", ["..", "%2E%2E", "a%2Fb", "%2Fetc%2Fpasswd"])
def test_a_folder_that_is_not_one_name_is_404(fs, name):
    assert fs.get(f"/api/work/{name}").status == 404


# -- Jira mode, through the recording backend -------------------------------------------------


def test_jira_mode_project(jira):
    project = ok(jira.served.get("/api/project"))
    assert project["recordOwner"] == "backend"
    assert project["user"] == ME
    assert project["people"] == {ME: NAMES[ME]}
    assert project["inboxItems"] is False
    assert project["createFields"] == ["priority"]
    external = {s["name"] for s in project["stages"] if s["external"]}
    assert external == set(jira.backend.external_stages)


def test_jira_mode_project_survives_a_failing_user_and_fields(jira):
    jira.backend.fail["current_user"] = Unreachable("Jira is unreachable")
    jira.stubs.create_fields = lambda backend: (_ for _ in ()).throw(
        Unreachable("Jira is unreachable"))
    served = jira.served
    served.server.services = jira.services()
    project = ok(served.get("/api/project"))
    assert project["user"] is None and project["people"] == {}
    assert project["createFields"] == {"unavailable": "Jira is unreachable"}


def test_jira_board_is_one_list_with_names(jira):
    board = ok(jira.served.get("/api/work"))
    assert len(jira.backend.named("list")) == 1
    assert {i["full-id"] for i in board["items"]} == {"tcw.work/TCW-1-first", "tcw.work/TCW-2-second"}
    assert board["people"] == {"acc-ann": NAMES["acc-ann"], ME: NAMES[ME]}


def test_jira_board_tags_are_a_backend_query(jira):
    board = ok(jira.served.get("/api/work?tag=ui"))
    tagged = [c for c in jira.backend.named("list") if c[1].tags is not None]
    assert len(tagged) == 1 and tagged[0][1].tags == frozenset({"ui"})
    assert [i["full-id"] for i in board["items"]] == ["tcw.work/TCW-1-first"]


def test_jira_item(jira):
    found = ok(jira.served.get("/api/work/TCW-1-first"))
    assert found["requestText"] == "Please do the first thing."
    assert [c["text"] for c in found["comments"]] == ["first comment", "second comment"]
    assert [c["author"] for c in found["comments"]] == ["acc-ann", "acc-bob"]
    assert found["people"] == {"acc-ann": NAMES["acc-ann"], "acc-bob": NAMES["acc-bob"]}
    assert found["link"] == {"label": "Jira",
                             "url": f"{SITE}/browse/TCW-1"}
    assert jira.backend.named("read_comments") == [("read_comments", "TCW-1-first", 200)]
    stages = [f["stage"] for f in found["files"] if f["stage"]]
    assert not set(stages) & set(jira.backend.external_stages)
    assert not keys_at_every_depth(found) & STAGE_NAMES


def test_a_jira_key_names_its_folder(jira):
    found = ok(jira.served.get("/api/work/TCW-1"))
    assert found["folder"] == "TCW-1-first"


@pytest.mark.parametrize("failure", [
    Unreachable("Jira is unreachable"),
    BackendError("set TCW_JIRA_TOKEN to read Jira"),
])
def test_jira_mode_degrades_when_the_backend_cannot_answer(jira, failure):
    for name in ("list", "read", "read_request", "read_comments"):
        jira.backend.fail[name] = failure
    board = ok(jira.served.get("/api/work"))
    assert board["fallback"] is True
    assert board["unavailable"] == str(failure)
    assert sorted(r["full-id"] for r in board["items"]) == \
        ["tcw.work/TCW-1-first", "tcw.work/TCW-2-second"]
    assert all(set(r) == {"full-id", "owner", "path"} for r in board["items"])
    found = ok(jira.served.get("/api/work/TCW-1-first"))
    for part in ("item", "requestText", "comments"):
        assert found[part] == {"unavailable": str(failure)}, part
    assert found["files"] and found["link"]
    assert jira.served.get("/api/work/TCW-9-nothing").status == 404


def test_not_found_never_degrades(jira):
    jira.backend.fail["read"] = NotFound("no work item tcw.work/TCW-1-first")
    answer = jira.served.get("/api/work/TCW-1-first")
    assert answer.status == 404 and answer.json["code"] == "not-found"


def test_filesystem_mode_never_degrades(fs, monkeypatch, tcw):
    folder = new(tcw, fs.root, "Thing")
    from tcw.work.fs_backend import FsWorkBackend

    def broken(self, *args, **kwargs):
        raise Unreachable("cannot answer")

    monkeypatch.setattr(FsWorkBackend, "read_comments", broken)
    answer = fs.get(f"/api/work/{folder}")
    assert answer.status == 503 and answer.json["code"] == "unreachable"


def test_jira_item_shows_when_only_the_other_items_cannot_be_read(jira):
    """`read` answers and `list` does not: the item still shows, `blocks`
    and `children` are empty, and the page is told why (Design 5.2)."""
    jira.backend.fail["list"] = Unreachable("could not reach the tracker")
    found = ok(jira.served.get("/api/work/TCW-1-first"))
    assert found["item"]["title"] == "First"
    assert (found["item"]["blocks"], found["item"]["children"]) == ([], [])
    assert any("could not reach the tracker" in w for w in found["warnings"]), found


def test_an_unexpected_value_error_is_a_500_without_a_traceback(jira):
    jira.backend.fail["read"] = ValueError("something TCW did not expect")
    answer = jira.served.get("/api/work/TCW-1-first")
    assert answer.status == 500 and answer.json["code"] == "error"
    assert answer.json["error"] == "something TCW did not expect"
    assert "Traceback" not in answer.text


# -- folders that are not items ----------------------------------------------------------------


def test_a_stray_folder_is_not_an_item(fs, tcw):
    folder = new(tcw, fs.root, "Real")
    (fs.root / "docs" / "work" / "notes").mkdir()
    assert fs.get("/api/work/notes").status == 404
    assert ok(fs.get(f"/api/work/{folder}"))["folder"] == folder


def test_a_stray_folder_is_not_on_the_fallback_board(jira):
    (jira.root / "docs" / "work" / "notes").mkdir()
    jira.backend.fail["list"] = Unreachable("could not reach the tracker")
    board = ok(jira.served.get("/api/work"))
    assert board["fallback"] is True
    assert sorted(r["full-id"] for r in board["items"]) == \
        ["tcw.work/TCW-1-first", "tcw.work/TCW-2-second"]


# -- a parent that is not here (TCW-109 Design 3.4, AC 32) -------------------------------


def _with_parents(root, parents, work=None):
    from tests.projectfiles import config_file, write_config_file
    document = yaml.safe_load(config_file(root).read_text())
    document["parents"] = parents
    if work is not None:
        document["work"] = work
    write_config_file(config_file(root), yaml.safe_dump(document, sort_keys=False))
    return root


def test_ac32_undecided_tags_do_not_stop_the_project_summary(tmp_path, serve_project):
    decided = ok(serve_project(fs_project(tmp_path / "d", "app", tags=())).get(
        "/api/project"))
    app = _with_parents(fs_project(tmp_path / "u", "app", config={}), ["core"])
    served = serve_project(app)
    project = ok(served.get("/api/project"))
    assert set(project["tags"]) == {"unavailable"}
    assert "(work.tags)" in project["tags"]["unavailable"]
    for key in decided:
        if key not in ("tags", "user"):
            assert project[key] == decided[key], key
    assert served.get("/api/work").status == 200


def test_ac32_undecided_jira_settings_stop_the_work_routes(tmp_path, serve_project):
    from tests.test_inherited_config import jira_mode
    app = _with_parents(fs_project(tmp_path, "app", config={}), ["core"],
                        jira_mode(jira={"project": "APP"}))
    answer = serve_project(app).get("/api/work")
    # 503, as every `InheritedUnavailable` an API request raises is
    # answered (TCW-112 Design 4.5).
    assert (answer.status, answer.json["code"]) == (503, "inherited-unavailable")
    assert "(work.jira)" in answer.json["error"]
