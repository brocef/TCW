"""TCW-113 Design 6.1, 6.2 and 3.5 (plan Step 13): the read routes take
`scope` and `project`, the list routes answer an object, `GET /api/project`
names each scope's projects, and one request is one command. AC 33. The
family is `F` (`tests/families.py`); `tcw serve` runs in `shared` unless a
test says otherwise."""

from __future__ import annotations

import os
import threading
from urllib.parse import quote

import pytest

import tcw.work.jira.client as jira_client
from tests.families import build_family, item_folder, jira_mode
from tests.work.jira.fake import FakeJira

DOWN = ["shared", "desktop", "server", "mobile"]


@pytest.fixture
def family(tmp_path):
    return build_family(tmp_path, docs_passes="none")


@pytest.fixture
def shared(family, serve_project):
    return serve_project(family["shared"])


def holds(web: dict, cli: dict) -> bool:
    """The web record holds every key of the CLI record, with its value."""
    return all(key in web and web[key] == value for key, value in cli.items())


def unavailable(answer: dict) -> list[str]:
    return [p["id"] for p in answer["projects"] if "unavailable" in p]


# -- AC 33 ------------------------------------------------------------------------------


def test_ac33_the_capability_list_holds_the_cli_records_in_order(family, shared):
    answer = shared.get("/api/capabilities?scope=down")
    assert answer.status == 200, answer.body
    cli = family.run("shared", "capabilities", "list", "--scope", "down", "--json")
    assert cli.code == 0, cli.err
    web, records = answer.json["capabilities"], cli.json["capabilities"]
    assert [r["full-id"] for r in web] == [r["full-id"] for r in records]
    assert all(holds(w, c) for w, c in zip(web, records))
    assert any("statuses" in r for r in web)
    assert unavailable(answer.json) == ["mobile"]
    assert answer.json["projects"] == cli.json["projects"]


def test_ac33_with_no_scope_the_list_is_the_projects_own(family, shared):
    answer = shared.get("/api/capabilities")
    assert answer.status == 200
    assert "projects" not in answer.json
    cli = family.run("shared", "capabilities", "list", "--json").json["capabilities"]
    web = answer.json["capabilities"]
    assert [r["full-id"] for r in web] == [r["full-id"] for r in cli]
    assert all(holds(w, c) for w, c in zip(web, cli))
    # The server's other fields are kept beside the record's (plan choice 9).
    assert all("modified" in r for r in web)


@pytest.mark.parametrize("query", ["scope=sideways", "scope=down&project=other"])
def test_ac33_a_refused_scope_or_project_is_a_usage_error(shared, query):
    for route in ("/api/work", "/api/taxonomy", "/api/capabilities",
                  "/api/capabilities/abc"):
        answer = shared.get(f"{route}?{query}")
        assert answer.status == 400, (route, answer.body)
        assert answer.json["code"] == "usage"


def test_a_project_no_scope_covers_is_refused_with_the_clis_message(family, shared):
    answer = shared.get("/api/work?scope=down&project=nosuch")
    assert answer.status == 400 and answer.json["code"] == "usage"
    cli = family.run("shared", "work", "list", "--scope", "down", "--project", "nosuch")
    assert cli.code == 2
    assert answer.json["error"] in cli.err


def test_ac33_the_project_names_each_scopes_projects(shared):
    scopes = shared.get("/api/project").json["scopes"]
    assert scopes["down"] == DOWN
    assert scopes["own"] == ["shared"]
    assert scopes["up"] == ["docs", "shared"]
    assert scopes["all"] == ["docs", *DOWN]


def test_ac33_the_board_holds_the_cli_items(family, shared):
    answer = shared.get("/api/work?scope=down")
    assert answer.status == 200, answer.body
    cli = family.run("shared", "work", "list", "--scope", "down", "--json")
    assert cli.code == 0, cli.err
    assert answer.json["items"] == cli.json["items"]
    assert [i["owner"] for i in answer.json["items"]] == ["shared", "desktop", "server"]
    assert unavailable(answer.json) == ["mobile"]
    assert answer.json["fallback"] is False


def test_ac33_the_board_under_all_and_with_a_tag(family, shared):
    family.item("desktop", "2026-10-02-tagged", tags=["ui"])
    for query, argv in (("scope=all&all=1", ["--scope", "all", "--all"]),
                        ("scope=down&tag=ui", ["--scope", "down", "--tag", "ui"]),
                        ("scope=down&project=desktop", ["--scope", "down", "--project",
                                                        "desktop"])):
        answer = shared.get(f"/api/work?{query}")
        assert answer.status == 200, answer.body
        cli = family.run("shared", "work", "list", *argv, "--json")
        assert cli.code == 0, cli.err
        assert answer.json["items"] == cli.json["items"], query


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setenv("TCW_TEST_JIRA_EMAIL", "dev@example.test")
    monkeypatch.setenv("TCW_TEST_JIRA_TOKEN", "token")
    fake = FakeJira().install(monkeypatch)
    fake.account("dev@example.test", "a-1", "Ann")
    return fake


def test_ac33_the_fallback_is_the_served_projects_alone(family, fake, serve_project):
    jira_mode(family, "desktop", fake)
    fake.unreachable()
    answer = serve_project(family["shared"]).get("/api/work?scope=down")
    assert answer.status == 200, answer.body
    assert answer.json["fallback"] is False
    assert unavailable(answer.json) == ["desktop", "mobile"]
    assert [i["owner"] for i in answer.json["items"]] == ["shared", "server"]
    own = serve_project(family["desktop"]).get("/api/work")
    assert own.status == 200, own.body
    assert own.json["fallback"] is True


# -- the tree routes ----------------------------------------------------------------------


def test_up_lists_the_inherited_terms_and_own_lists_none(family, serve_project):
    desktop = serve_project(family["desktop"])
    up = desktop.get("/api/taxonomy?scope=up")
    assert up.status == 200
    assert [t["full-id"] for t in up.json["terms"]] == ["shared.taxonomy/invoice"]
    assert [p["id"] for p in up.json["projects"]] == ["docs", "shared", "desktop"]
    own = desktop.get("/api/taxonomy")
    assert own.status == 200
    assert own.json == {"terms": []}


def test_a_detail_under_down_carries_statuses_and_overridden_by(family, shared):
    answer = shared.get("/api/capabilities/abc?scope=down")
    assert answer.status == 200, answer.body
    cli = family.run("shared", "capabilities", "show", "abc", "--scope", "down", "--json")
    assert cli.code == 0, cli.err
    record = answer.json["capability"]
    assert holds(record, cli.json["capability"])
    assert record["statuses"] == cli.json["capability"]["statuses"]
    assert record["overridden-by"] == ["desktop.capabilities/abc",
                                       "server.capabilities/abc"]
    assert unavailable(answer.json) == ["mobile"]
    assert {"coreRevision", "declaredDescription"} <= set(answer.json)


def test_with_no_scope_a_detail_carries_neither(shared):
    answer = shared.get("/api/capabilities/abc")
    assert answer.status == 200
    assert "statuses" not in answer.json["capability"]
    assert "overridden-by" not in answer.json["capability"]
    assert "projects" not in answer.json


@pytest.mark.parametrize("declared", ["Desktop's own words.\n", None])
def test_another_projects_capability_is_read_from_its_owner(family, serve_project,
                                                            declared):
    if declared is not None:
        (family["desktop"] / "docs" / "capabilities" / "abc" / "description.md"
         ).write_text(declared, encoding="utf-8")
    key = quote("desktop.capabilities/abc", safe="")
    answer = serve_project(family["shared"]).get(f"/api/capabilities/{key}?scope=down")
    assert answer.status == 200, answer.body
    assert answer.json["capability"]["full-id"] == "desktop.capabilities/abc"
    assert answer.json["declaredDescription"] == (
        None if declared is None else declared.strip())
    own = serve_project(family["desktop"]).get("/api/capabilities/abc")
    assert own.status == 200
    assert answer.json["coreRevision"] == own.json["coreRevision"]


def test_a_term_detail_under_up_holds_the_cli_record(family, serve_project):
    desktop = serve_project(family["desktop"])
    answer = desktop.get("/api/taxonomy/invoice?scope=up")
    assert answer.status == 200, answer.body
    cli = family.run("desktop", "taxonomy", "show", "invoice", "--scope", "up", "--json")
    assert holds(answer.json["term"], cli.json["term"])
    assert answer.json["coreRevision"]


# -- work items ---------------------------------------------------------------------------


def test_an_items_children_follow_the_scope(family, shared):
    family.item("shared", "2026-10-05-epic")
    family.item("desktop", "2026-10-06-part", parent="shared.work/2026-10-05-epic")
    alone = shared.get("/api/work/2026-10-05-epic")
    assert alone.status == 200
    assert alone.json["item"]["children"] == []
    assert "projects" not in alone.json
    down = shared.get("/api/work/2026-10-05-epic?scope=down")
    assert down.status == 200, down.body
    assert down.json["item"]["children"] == ["desktop.work/2026-10-06-part"]
    assert unavailable(down.json) == ["mobile"]
    assert any("'mobile'" in w for w in down.json["warnings"])


# -- one request is one command (Design 3.5, plan choice 10) ----------------------------


@pytest.fixture
def searches(fake, monkeypatch):
    """Each item search sent to the fake, as (jql, fields, thread)."""
    sent = []
    answer = jira_client.JiraClient._request

    def request(client, method, path, body=None, *, timeout=None):
        if method == "POST" and path.endswith("/search/jql") \
                and "key in" not in body["jql"].lower():
            sent.append((body["jql"], tuple(body.get("fields", ())),
                         threading.get_ident()))
        return answer(client, method, path, body, timeout=timeout)
    monkeypatch.setattr(jira_client.JiraClient, "_request", request)
    return sent


@pytest.fixture
def in_jira(family, fake):
    for pid in ("shared", "desktop", "server"):
        jira_mode(family, pid, fake)
    return family


def test_one_request_makes_each_search_once(in_jira, serve_project, searches):
    answer = serve_project(in_jira["shared"]).get("/api/work?scope=down")
    assert answer.status == 200, answer.body
    assert len(answer.json["items"]) == 3
    made = [(jql, fields) for jql, fields, _ in searches]
    assert made and len(made) == len(set(made))


def test_concurrent_requests_each_make_their_own_searches(in_jira, serve_project,
                                                          searches):
    served = serve_project(in_jira["shared"])
    assert served.get("/api/work?scope=down").status == 200
    one = len(searches)
    searches.clear()
    answers = []
    threads = [threading.Thread(target=lambda: answers.append(
        served.get("/api/work?scope=down"))) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert [a.status for a in answers] == [200, 200]
    assert len(searches) == 2 * one
    assert len({thread for _, _, thread in searches}) == 2


def test_nothing_is_kept_after_a_request(in_jira, serve_project, searches):
    served = serve_project(in_jira["shared"])
    assert served.get("/api/work?scope=down").status == 200
    one = len(searches)
    assert served.get("/api/work?scope=down").status == 200
    assert len(searches) == 2 * one
    from tcw.config import command_state
    assert command_state() is None
    assert os.environ["TCW_TEST_JIRA_EMAIL"] == "dev@example.test"


def test_the_shared_items_are_the_ones_listed(in_jira, serve_project):
    answer = serve_project(in_jira["shared"]).get("/api/work?scope=down")
    owners = [i["owner"] for i in answer.json["items"]]
    assert owners == ["shared", "desktop", "server"]
    assert all(item_folder(o) in i["full-id"] for o, i in zip(owners, answer.json["items"]))
